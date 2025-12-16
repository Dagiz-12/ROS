import requests
import json

BASE_URL = "http://localhost:8000/api"


def print_response(response):
    print(f"Status: {response.status_code}")
    if response.text:
        try:
            print("Response:", json.dumps(response.json(), indent=2))
        except:
            print("Response:", response.text)
    print("-" * 50)


def test_authentication():
    print("=== Testing Authentication ===")

    # Test login
    login_data = {"username": "waiter1", "password": "waiter123"}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    print_response(response)

    if response.status_code == 200:
        token = response.json().get('token')
        user_data = response.json().get('user')
        print(f"Token received: {token[:50]}...")
        return token, user_data

    return None, None


def test_restaurant_endpoints(token):
    print("\n=== Testing Restaurant Endpoints ===")

    headers = {"Authorization": f"Bearer {token}"}

    # Get user's restaurant
    response = requests.get(
        f"{BASE_URL}/restaurants/my-restaurant/", headers=headers)
    print("My Restaurant:")
    print_response(response)

    # Get all restaurants (admin only)
    response = requests.get(
        f"{BASE_URL}/restaurants/restaurants/", headers=headers)
    print("All Restaurants:")
    print_response(response)

    return response.json()[0]['id'] if response.status_code == 200 and response.json() else None


def test_branch_endpoints(token, restaurant_id):
    print("\n=== Testing Branch Endpoints ===")

    headers = {"Authorization": f"Bearer {token}"}

    # Get user's branch
    response = requests.get(
        f"{BASE_URL}/restaurants/my-branch/", headers=headers)
    print("My Branch:")
    print_response(response)

    # Get branches for a restaurant
    if restaurant_id:
        response = requests.get(
            f"{BASE_URL}/restaurants/restaurants/{restaurant_id}/branches/",
            headers=headers
        )
        print("Restaurant Branches:")
        print_response(response)


def test_menu_endpoints(token, restaurant_id):
    print("\n=== Testing Menu Endpoints ===")

    headers = {"Authorization": f"Bearer {token}"}

    # Get restaurant menu (authenticated)
    response = requests.get(
        f"{BASE_URL}/menu/restaurant-menu/", headers=headers)
    print("Restaurant Menu (Authenticated):")
    print_response(response)

    # Get public menu (no auth required)
    if restaurant_id:
        response = requests.get(f"{BASE_URL}/menu/public/{restaurant_id}/")
        print("Public Menu:")
        print_response(response)

    # Search menu items
    search_params = {"query": "wot", "available_only": "true"}
    response = requests.get(
        f"{BASE_URL}/menu/items/search/", headers=headers, params=search_params)
    print("Menu Search (query='wot'):")
    print_response(response)


def test_core_endpoints():
    print("\n=== Testing Core Endpoints ===")

    # Health check (no auth required)
    response = requests.get(f"{BASE_URL}/core/health/")
    print("Health Check:")
    print_response(response)

    # System stats (requires admin - will likely fail for waiter)
    headers = {"Authorization": f"Bearer {token}" if 'token' in locals()
               else ""}
    response = requests.get(f"{BASE_URL}/core/system/stats/", headers=headers)
    print("System Stats (waiter should be denied):")
    print_response(response)


if __name__ == "__main__":
    print("=== Restaurant Ordering System API Tests ===\n")

    # Test authentication
    token, user_data = test_authentication()

    if token:
        print(f"Logged in as: {user_data['username']} ({user_data['role']})")

        # Test restaurant endpoints
        restaurant_id = test_restaurant_endpoints(token)

        # Test branch endpoints
        test_branch_endpoints(token, restaurant_id)

        # Test menu endpoints
        test_menu_endpoints(token, restaurant_id)

        # Test core endpoints
        test_core_endpoints()

        print("\n✅ All tests completed!")
    else:
        print(
            "\n❌ Authentication failed! Make sure to run: python manage.py setup_dev_data")
