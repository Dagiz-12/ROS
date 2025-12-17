"""
Test complete order flow: QR → Waiter → Chef → Cashier
"""

import requests
import json
import time


class RestaurantTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.tokens = {}

    def login_all_roles(self):
        """Login as all test users"""
        users = [
            ('waiter1', 'waiter123', 'waiter'),
            ('chef1', 'chef123', 'chef'),
            ('cashier1', 'cashier123', 'cashier'),
            ('manager1', 'manager123', 'manager'),
        ]

        for username, password, role in users:
            response = requests.post(
                f"{self.base_url}/api/auth/login/",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                token = response.json().get('access')
                self.tokens[role] = token
                print(f"✅ {role.capitalize()} logged in")
            else:
                print(
                    f"❌ {role.capitalize()} login failed: {response.status_code}")

    def test_qr_menu(self):
        """Test QR menu access"""
        print("\n1. Testing QR Menu (Public Access)...")
        response = requests.get(f"{self.base_url}/api/tables/qr-menu/1/1/")
        if response.status_code == 200:
            print("✅ QR menu accessible")
        else:
            print(f"❌ QR menu failed: {response.status_code}")

    def test_waiter_interface(self):
        """Test waiter interfaces"""
        print("\n2. Testing Waiter Interfaces...")

        headers = {"Authorization": f"Bearer {self.tokens.get('waiter')}"}

        # Test dashboard
        response = requests.get(
            f"{self.base_url}/api/tables/waiter/dashboard/", headers=headers)
        print(
            f"   Dashboard: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")

        # Test tables view
        response = requests.get(
            f"{self.base_url}/api/tables/waiter/tables/", headers=headers)
        print(
            f"   Tables: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")

        # Test orders view
        response = requests.get(
            f"{self.base_url}/api/tables/waiter/orders/", headers=headers)
        print(
            f"   Orders: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")

    def test_chef_interface(self):
        """Test chef interface"""
        print("\n3. Testing Chef Interface...")

        headers = {"Authorization": f"Bearer {self.tokens.get('chef')}"}
        response = requests.get(
            f"{self.base_url}/api/tables/chef/dashboard/", headers=headers)
        print(
            f"   Kitchen Display: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")

    def test_cashier_interface(self):
        """Test cashier interface"""
        print("\n4. Testing Cashier Interface...")

        headers = {"Authorization": f"Bearer {self.tokens.get('cashier')}"}
        response = requests.get(
            f"{self.base_url}/api/tables/cashier/dashboard/", headers=headers)
        print(
            f"   Payment System: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")

    def test_admin_panel(self):
        """Test admin panel"""
        print("\n5. Testing Admin Panel...")

        headers = {"Authorization": f"Bearer {self.tokens.get('manager')}"}
        response = requests.get(
            f"{self.base_url}/restaurant-admin/dashboard/", headers=headers)
        print(
            f"   Admin Dashboard: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")

    def test_api_endpoints(self):
        """Test key API endpoints"""
        print("\n6. Testing API Endpoints...")

        headers = {"Authorization": f"Bearer {self.tokens.get('waiter')}"}

        endpoints = [
            ("/api/tables/tables/", "GET"),
            ("/api/tables/orders/", "GET"),
            ("/api/menu/restaurant-menu/", "GET"),
            ("/api/restaurants/my-restaurant/", "GET"),
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = requests.get(
                    f"{self.base_url}{endpoint}", headers=headers)
                print(
                    f"   {endpoint}: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("COMPLETE SYSTEM TEST")
        print("=" * 60)

        self.login_all_roles()
        self.test_qr_menu()
        self.test_waiter_interface()
        self.test_chef_interface()
        self.test_cashier_interface()
        self.test_admin_panel()
        self.test_api_endpoints()

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print("Next steps:")
        print("1. Fix any failing tests above")
        print("2. Test actual order flow manually")
        print("3. Check authentication token format")
        print("4. Verify all templates are accessible")


if __name__ == "__main__":
    tester = RestaurantTester()
    tester.run_all_tests()
