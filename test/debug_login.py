# debug_login.py
import requests
import json


def test_login_flow():
    """Test complete login flow"""
    BASE_URL = "http://localhost:8000"
    session = requests.Session()

    print("Testing Login Flow")
    print("=" * 60)

    # 1. First get CSRF token by visiting login page
    print("\n1. Getting CSRF token...")
    login_page = session.get(f"{BASE_URL}/login/")
    csrf_token = None

    # Try to find CSRF token in cookies or form
    if 'csrftoken' in session.cookies:
        csrf_token = session.cookies['csrftoken']
        print(f"   ✅ CSRF token from cookie: {csrf_token[:20]}...")

    # 2. Test login
    print("\n2. Testing login...")
    login_data = {
        'username': 'waiter1',
        'password': 'waiter123'
    }

    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token if csrf_token else ''
    }

    response = session.post(
        f"{BASE_URL}/api/auth/login/",
        json=login_data,
        headers=headers
    )

    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Login successful")
        print(f"   Token: {data.get('token', 'No token')[:30]}...")

        # 3. Test accessing protected page
        print("\n3. Testing protected page access...")
        dashboard_response = session.get(f"{BASE_URL}/waiter/dashboard/")
        print(f"   Dashboard status: {dashboard_response.status_code}")

        if dashboard_response.status_code == 200:
            print(f"   ✅ Can access dashboard")
            print(f"   Page title: ", end="")
            # Extract title from HTML
            import re
            title_match = re.search(
                r'<title>(.*?)</title>', dashboard_response.text)
            if title_match:
                print(title_match.group(1))
        else:
            print(f"   ❌ Cannot access dashboard")
            print(f"   Response: {dashboard_response.text[:500]}")

        # 4. Test logout
        print("\n4. Testing logout...")

        # Try JWT logout
        if 'token' in data:
            logout_headers = {
                'Authorization': f"Bearer {data['token']}",
                'X-CSRFToken': csrf_token if csrf_token else ''
            }
            logout_response = session.post(
                f"{BASE_URL}/api/auth/logout/",
                headers=logout_headers
            )
            print(f"   JWT logout status: {logout_response.status_code}")

        # Try session logout
        logout_response = session.post(f"{BASE_URL}/api/auth/logout/")
        print(f"   Session logout status: {logout_response.status_code}")

        # Clear session
        session.cookies.clear()

        # 5. Test access after logout
        print("\n5. Testing access after logout...")
        after_logout_response = session.get(f"{BASE_URL}/waiter/dashboard/")
        print(f"   Status after logout: {after_logout_response.status_code}")

        if after_logout_response.status_code in [302, 401, 403]:
            print(f"   ✅ Properly logged out (redirected or denied)")
        else:
            print(f"   ⚠️ Still have access after logout")

    else:
        print(f"   ❌ Login failed")
        print(f"   Headers sent: {headers}")
        print(f"   Cookies in session: {dict(session.cookies)}")


if __name__ == "__main__":
    test_login_flow()
