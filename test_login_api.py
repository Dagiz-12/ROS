# test_login_api.py
import requests
import json


def test_login_api():
    """Test the login API endpoint"""
    print("=" * 60)
    print("TESTING LOGIN API")
    print("=" * 60)

    BASE_URL = "http://localhost:8000"

    # Test with waiter credentials
    print("\n1. Testing with waiter credentials...")
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
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n   ✅ LOGIN SUCCESSFUL!")
            print(f"   Response keys: {list(data.keys())}")

            # Check for token in different possible fields
            for key in ['token', 'access', 'access_token', 'accessToken']:
                if key in data:
                    print(
                        f"   Token found in '{key}' field: {data[key][:50]}...")

            # Check user data
            if 'user' in data:
                print(f"   User data: {data['user']}")

        elif response.status_code == 401:
            print(f"\n   ❌ 401 UNAUTHORIZED")
            print(f"   This means: Invalid username or password")

        elif response.status_code == 403:
            print(f"\n   ❌ 403 FORBIDDEN")
            print(f"   This means: User exists but permissions issue")
            print(f"   Possible causes:")
            print(f"   - User is not active")
            print(f"   - Account is locked")
            print(f"   - CSRF token missing (if using session auth)")

    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")

    # Test with incorrect credentials
    print("\n2. Testing with incorrect credentials...")
    login_data = {
        'username': 'wronguser',
        'password': 'wrongpass'
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Expected: 401 (for wrong credentials)")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test without JSON header
    print("\n3. Testing without JSON header...")
    login_data = {
        'username': 'waiter1',
        'password': 'waiter123'
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login/",
            data=login_data  # Not JSON
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")


if __name__ == "__main__":
    test_login_api()
