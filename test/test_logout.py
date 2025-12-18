# test_logout.py
import requests


def test_logout():
    """Test logout functionality"""
    BASE_URL = "http://localhost:8000"
    session = requests.Session()

    print("Testing Logout Functionality")
    print("=" * 50)

    # 1. Login first
    print("\n1. Logging in...")
    login_data = {'username': 'waiter1', 'password': 'waiter123'}

    login_response = session.post(
        f"{BASE_URL}/api/auth/login/",
        json=login_data
    )

    if login_response.status_code == 200:
        print("   ✅ Login successful")

        # Get CSRF token from cookies
        csrf_token = session.cookies.get('csrftoken', '')

        # 2. Test logout API
        print("\n2. Testing logout API...")

        logout_headers = {
            'X-CSRFToken': csrf_token,
            'Content-Type': 'application/json'
        }

        logout_response = session.post(
            f"{BASE_URL}/api/auth/logout/",
            headers=logout_headers
        )

        print(f"   Logout status: {logout_response.status_code}")
        print(f"   Logout response: {logout_response.text}")

        if logout_response.status_code == 200:
            print("   ✅ Logout API successful")
        else:
            print("   ❌ Logout API failed")

        # 3. Test accessing protected page after logout
        print("\n3. Testing access after logout...")
        dashboard_response = session.get(f"{BASE_URL}/waiter/dashboard/")

        if dashboard_response.status_code in [302, 401, 403]:
            print(
                f"   ✅ Properly logged out (status: {dashboard_response.status_code})")
        else:
            print(
                f"   ⚠️ Still have access (status: {dashboard_response.status_code})")

    else:
        print(f"   ❌ Login failed: {login_response.status_code}")


if __name__ == "__main__":
    test_logout()
