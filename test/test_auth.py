import requests
import json

BASE_URL = "http://localhost:8000/api/auth"


def test_registration():
    """Test user registration"""
    data = {
        "username": "testwaiter",
        "email": "waiter@restaurant.com",
        "password": "test123",
        "password2": "test123",
        "first_name": "Test",
        "last_name": "Waiter",
        "role": "waiter",
        "phone": "+251911223344"
    }

    response = requests.post(f"{BASE_URL}/register/", json=data)
    print("Registration Response:", response.json())
    return response.json().get('token') if response.status_code == 201 else None


def test_login():
    """Test user login"""
    data = {
        "username": "testwaiter",
        "password": "test123"
    }

    response = requests.post(f"{BASE_URL}/login/", json=data)
    print("Login Response:", response.json())
    return response.json().get('token') if response.status_code == 200 else None


def test_profile(token):
    """Test getting user profile with token"""
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{BASE_URL}/profile/", headers=headers)
    print("Profile Response:", response.json())


def test_admin_endpoints(admin_token):
    """Test admin endpoints"""
    headers = {
        "Authorization": f"Bearer {admin_token}"
    }

    # List all users
    response = requests.get(f"{BASE_URL}/users/", headers=headers)
    print("Users List:", response.json())


if __name__ == "__main__":
    print("=== Testing Authentication System ===\n")

    # Test registration
    token = test_registration()

    if token:
        # Test profile with registration token
        test_profile(token)

        # Test login with same credentials
        login_token = test_login()

        if login_token:
            # Test profile with login token
            test_profile(login_token)

            print("\n✅ Authentication system working correctly!")
        else:
            print("\n❌ Login failed!")
    else:
        print("\n❌ Registration failed!")
