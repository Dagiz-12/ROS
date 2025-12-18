# test_access.py
import requests
import json


def test_staff_interfaces():
    """Test accessing staff interfaces with login"""
    BASE_URL = "http://localhost:8000"

    print("Testing Staff Interface Access")
    print("=" * 50)

    # 1. Login to get token
    print("\n1. Logging in as waiter...")
    login_data = {'username': 'waiter1', 'password': 'waiter123'}

    response = requests.post(
        f"{BASE_URL}/api/auth/login/",
        json=login_data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        token = response.json()['token']
        print(f"   ✅ Token obtained: {token[:50]}...")

        # 2. Try to access waiter dashboard with session (not API token)
        print("\n2. Testing waiter dashboard access...")

        # Create a session to maintain cookies
        session = requests.Session()

        # First login with session (for Django session auth)
        login_response = session.post(
            f"{BASE_URL}/api/auth/login/",
            json=login_data
        )

        if login_response.status_code == 200:
            print(f"   ✅ Session login successful")

            # Try to access the template view
            dashboard_response = session.get(f"{BASE_URL}/waiter/dashboard/")
            print(f"   Dashboard status: {dashboard_response.status_code}")
            print(f"   Response length: {len(dashboard_response.text)} chars")

            if dashboard_response.status_code == 200:
                print(f"   ✅ SUCCESS! Can access waiter dashboard")
            else:
                print(f"   ❌ Failed to access dashboard")
                print(f"   Response: {dashboard_response.text[:500]}")
        else:
            print(f"   ❌ Session login failed")

    else:
        print(f"   ❌ Login failed: {response.status_code}")


if __name__ == "__main__":
    test_staff_interfaces()
