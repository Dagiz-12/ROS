# fix_auth_debug.py - Corrected version
import requests
import json


def debug_auth():
    """Debug authentication token issues"""
    print("Debugging Authentication Token Issue")
    print("=" * 50)

    BASE_URL = "http://localhost:8000"

    # Test 1: Login with waiter credentials
    print("\n1. Testing login with waiter credentials...")
    login_data = {
        'username': 'waiter1',
        'password': 'waiter123'
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )

        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")

            # Check what keys are returned
            print(f"   Response keys: {list(data.keys())}")

            # Look for token in different possible locations
            token = None
            if 'token' in data:
                token = data['token']
                print(f"   ✓ Found token in 'token' field")
            elif 'access' in data:
                token = data['access']
                print(f"   ✓ Found token in 'access' field")
            elif 'access_token' in data:
                token = data['access_token']
                print(f"   ✓ Found token in 'access_token' field")
            else:
                print(f"   ✗ No token found in response")
                print(f"   Full response: {json.dumps(data, indent=2)}")

            if token:
                print(f"   Token received: {token[:50]}..." if len(
                    token) > 50 else f"   Token: {token}")

                # Test the token with a protected endpoint
                print("\n2. Testing token with protected endpoint...")

                # Try different header formats
                headers_formats = [
                    ('Bearer', f"Bearer {token}"),
                    ('Token', f"Token {token}"),
                    ('JWT', f"JWT {token}"),
                    ('Basic', f"Basic {token}")
                ]

                for format_name, header_value in headers_formats:
                    print(f"   Testing format: {format_name}")

                    test_response = requests.get(
                        f"{BASE_URL}/api/auth/profile/",
                        headers={
                            'Authorization': header_value,
                            'Content-Type': 'application/json'
                        }
                    )

                    print(f"     Status: {test_response.status_code}")

                    if test_response.status_code == 200:
                        print(f"     ✓ SUCCESS with {format_name} format!")
                        return format_name, header_value
                    elif test_response.status_code == 401:
                        print(f"     ✗ 401 Unauthorized with {format_name}")
                    elif test_response.status_code == 403:
                        print(f"     ✗ 403 Forbidden with {format_name}")
                    else:
                        print(
                            f"     ? {test_response.status_code} with {format_name}")

                print(f"\n   None of the header formats worked")
                return None, None
            else:
                print(f"\n   No token to test")
                return None, None
        else:
            print(f"   ✗ Login failed with status {response.status_code}")
            return None, None

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return None, None


def main():
    print("Authentication Debug Script")
    print("=" * 40)

    format_name, header_value = debug_auth()

    if format_name and header_value:
        print(f"\n✅ CORRECT HEADER FORMAT: {format_name}")
        print(f"✅ CORRECT HEADER VALUE: {header_value[:50]}...")

        print(f"\nUse this in your JavaScript:")
        print(f'headers: {{')
        print(f'    "Authorization": "{header_value}",')
        print(f'    "Content-Type": "application/json"')
        print(f'}}')
    else:
        print(f"\n❌ Could not determine correct header format")
        print(f"\nTroubleshooting steps:")
        print(f"1. Check if the login endpoint returns a token")
        print(f"2. Check the response format from /api/auth/login/")
        print(f"3. Verify the JWT implementation in accounts/utils.py")
        print(f"4. Check if users exist in database (waiter1/waiter123)")


if __name__ == "__main__":
    main()
