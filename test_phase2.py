"""
Fixed Phase 2 Testing Script - Adjusted for your URL patterns
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
TEST_DATA = {}


def print_section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")


def make_request(method, endpoint, data=None, token=None, is_public=False):
    """Helper function to make API requests"""
    headers = {}
    if token and not is_public:
        headers['Authorization'] = f'Bearer {token}'

    if data and method in ['POST', 'PUT', 'PATCH']:
        headers['Content-Type'] = 'application/json'

    url = f"{BASE_URL}{endpoint}"

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data)
        else:
            return None

        # Try to parse JSON response
        try:
            response_data = response.json()
        except:
            response_data = {'text': response.text}

        return {
            'status_code': response.status_code,
            'data': response_data,
            'headers': dict(response.headers)
        }
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {url}. Make sure server is running!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def login_user(username, password):
    """Login and get JWT token - Fixed based on your URL patterns"""
    print_section(f"Logging in as {username}")

    # Try different possible login endpoints
    endpoints = [
        '/api/auth/login/',  # Most likely
        '/api/auth/token/',  # Alternative
        '/auth/login/',      # Another possibility
        '/api/token/',       # DRF simple JWT
    ]

    data = {
        'username': username,
        'password': password
    }

    # Also try with 'email' field
    data_email = {
        'email': username,
        'password': password
    }

    for endpoint in endpoints:
        print(f"Trying endpoint: {endpoint}")

        # Try with username first
        result = make_request('POST', endpoint, data, is_public=True)

        if result and result['status_code'] == 200:
            # Check different possible token response formats
            token = result['data'].get('access') or result['data'].get(
                'token') or result['data'].get('access_token')
            if token:
                print(f"✅ Login successful! Token: {token[:50]}...")
                return token
            else:
                print(f"⚠️  No token in response: {result['data'].keys()}")

        # Try with email field
        result = make_request('POST', endpoint, data_email, is_public=True)
        if result and result['status_code'] == 200:
            token = result['data'].get('access') or result['data'].get(
                'token') or result['data'].get('access_token')
            if token:
                print(
                    f"✅ Login successful (with email)! Token: {token[:50]}...")
                return token

    print(f"❌ All login attempts failed for {username}")
    print("Check your auth endpoints in Django admin or urls.py")
    return None


def test_public_endpoints():
    """Test endpoints that don't require authentication - FIXED URLs"""
    print_section("Testing Public Endpoints")

    # 1. Test health check - Based on your URL patterns, it's /api/health/
    print("1. Testing health check...")
    result = make_request('GET', '/api/health/', is_public=True)
    if result and result['status_code'] == 200:
        print(f"✅ Health check: {result['data']}")
    else:
        print(f"⚠️  Health check: {result}")

    # 2. Test public menu - Based on your URL patterns
    print("\n2. Testing public menu endpoint...")
    endpoints = [
        '/api/menu/public/1/',
        '/api/menu/public/',
        '/menu/public/1/',
    ]

    for endpoint in endpoints:
        result = make_request('GET', endpoint, is_public=True)
        if result and result['status_code'] == 200:
            menu_data = result['data']
            # Handle different response formats
            menu_items = menu_data.get('items', []) or menu_data.get(
                'results', []) or menu_data
            if isinstance(menu_items, list):
                print(
                    f"✅ Public menu loaded from {endpoint}: {len(menu_items)} items")
                TEST_DATA['menu_items'] = menu_items
                if menu_items:
                    TEST_DATA['sample_menu_item'] = menu_items[0]
                break
            else:
                print(f"⚠️  Unexpected menu format: {type(menu_items)}")

    if not TEST_DATA.get('menu_items'):
        print("❌ Could not load public menu from any endpoint")


def explore_api_structure():
    """Explore the API to understand available endpoints"""
    print_section("Exploring API Structure")

    # List all endpoints from your URL patterns (shown in the error)
    print("Available endpoints from your URL patterns:")
    endpoints = [
        ('/api/auth/', 'Authentication endpoints'),
        ('/api/restaurants/', 'Restaurant management'),
        ('/api/menu/', 'Menu management'),
        ('/api/tables/', 'Table and order management'),
        ('/api/health/', 'Health check'),
        ('/api/system/info/', 'System info'),
        ('/api/system/stats/', 'System stats'),
    ]

    for endpoint, description in endpoints:
        print(f"  • {endpoint} - {description}")

    # Try to get a list of available endpoints
    print("\nTesting each endpoint group:")

    # Test authentication endpoints
    print("\n1. Authentication endpoints:")
    auth_endpoints = ['/api/auth/login/',
                      '/api/auth/register/', '/api/auth/users/']
    for endpoint in auth_endpoints:
        result = make_request('GET', endpoint, is_public=True)
        if result:
            print(f"  {endpoint}: {result['status_code']}")


def test_authentication_flow():
    """Test the complete authentication flow"""
    print_section("Testing Authentication Flow")

    # Try to register a test user first (if endpoint exists)
    print("1. Testing registration...")
    registration_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123',
        'role': 'waiter',
        'restaurant': 1,
        'branch': 1
    }

    result = make_request('POST', '/api/auth/register/',
                          registration_data, is_public=True)
    if result and result['status_code'] in [200, 201]:
        print(f"✅ Registration: {result['status_code']}")
    else:
        print(f"⚠️  Registration endpoint: {result}")

    # Test with provided test users
    print("\n2. Testing with pre-configured users:")
    test_users = [
        ('admin', 'admin123'),
        ('manager1', 'manager123'),
        ('chef1', 'chef123'),
        ('waiter1', 'waiter123'),
        ('cashier1', 'cashier123')
    ]

    for username, password in test_users:
        token = login_user(username, password)
        if token:
            TEST_DATA[f'{username}_token'] = token
            # Test profile endpoint with the token
            result = make_request('GET', '/api/auth/profile/', token=token)
            if result and result['status_code'] == 200:
                print(f"  ✅ {username} profile accessible")
                print(f"     Role: {result['data'].get('role')}")
                print(f"     Restaurant: {result['data'].get('restaurant')}")
            else:
                print(f"  ⚠️  {username} profile: {result}")


def quick_test_table_endpoints():
    """Quick test of table endpoints"""
    print_section("Testing Table Endpoints")

    # Try different table endpoint variations
    endpoints = [
        '/api/tables/tables/',
        '/api/tables/',
        '/tables/tables/',
    ]

    for endpoint in endpoints:
        print(f"\nTrying endpoint: {endpoint}")
        # Will fail without token
        result = make_request('GET', endpoint, is_public=False)
        if result:
            print(f"  Status: {result['status_code']}")
            if result['status_code'] == 401:
                print("  ⚠️  Requires authentication (as expected)")
            elif result['status_code'] == 200:
                print(f"  ✅ Accessible! Data: {len(result['data'])} items")
                break


def create_test_data_if_needed():
    """Create test data if database is empty"""
    print_section("Checking/Creating Test Data")

    # First, try to login as admin
    admin_token = login_user('admin', 'admin123')

    if not admin_token:
        print("❌ Cannot login as admin. Need to create superuser first.")
        print("\nRun these commands:")
        print("1. python manage.py createsuperuser")
        print("2. python manage.py setup_dev_data")
        return False

    print("✅ Admin access available")

    # Check if we have restaurants
    result = make_request(
        'GET', '/api/restaurants/restaurants/', token=admin_token)
    if result and result['status_code'] == 200:
        restaurants = result['data'].get(
            'results', result['data'].get('restaurants', []))
        if restaurants:
            print(f"✅ Found {len(restaurants)} restaurants")
            TEST_DATA['restaurant_id'] = restaurants[0]['id']
        else:
            print("⚠️  No restaurants found")

    return True


def run_fixed_test():
    """Run fixed test based on your URL structure"""
    print_section("PHASE 2 TEST - ADJUSTED FOR YOUR URLS")
    print(f"Base URL: {BASE_URL}")

    # First explore the API structure
    explore_api_structure()

    # Test public endpoints
    test_public_endpoints()

    # Test authentication
    test_authentication_flow()

    # Check if we need to create test data
    if not TEST_DATA.get('admin_token'):
        create_test_data_if_needed()

    # Quick test of table endpoints (will likely fail without proper auth)
    quick_test_table_endpoints()

    # Summary
    print_section("TEST SUMMARY")

    print("Successfully tested:")
    if TEST_DATA.get('menu_items') is not None:
        print(f"✅ Public menu: {len(TEST_DATA.get('menu_items', []))} items")

    tokens_found = [key for key in TEST_DATA.keys() if key.endswith('_token')]
    print(f"✅ Authentication: {len(tokens_found)} users logged in")

    print(f"\nAvailable test data:")
    for key, value in TEST_DATA.items():
        if 'token' in key:
            print(f"  {key}: {value[:30]}...")
        elif isinstance(value, (list, dict)):
            print(
                f"  {key}: {type(value).__name__} with {len(value) if isinstance(value, list) else len(value.keys())} items")
        else:
            print(f"  {key}: {value}")

    print(f"\n🎯 NEXT STEPS:")
    print("1. Ensure test users exist: admin/admin123, waiter1/waiter123, etc.")
    print("2. Run: python manage.py setup_dev_data")
    print("3. Check Django admin at http://localhost:8000/admin/")
    print("4. Test endpoints manually with curl or Postman")
    print("5. Fix any URL mismatches in your urls.py files")


if __name__ == "__main__":
    # Check if server is running
    print("Checking if server is available...")
    try:
        response = requests.get("http://localhost:8000", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running!")
        else:
            print(f"✅ Server is responding (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running or not accessible at http://localhost:8000")
        print("   Start server with: python manage.py runserver")
        sys.exit(1)

    # Run the fixed test
    run_fixed_test()
