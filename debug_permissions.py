# debug_permissions.py
from accounts.permissions import IsChefOrHigher, IsWaiterOrHigher, IsCashierOrHigher
from tables.models import Order
from accounts.models import CustomUser
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_system.settings')
django.setup()


def check_permissions():
    print("=" * 60)
    print("PERMISSION CHECK")
    print("=" * 60)

    # Get a chef user
    try:
        chef = CustomUser.objects.get(username='chef1')
        print(f"\n1. Chef User: {chef.username} (Role: {chef.role})")

        # Check if chef can access orders
        orders = Order.objects.all()[:5]
        print(f"\n2. Orders in system: {orders.count()}")

        for order in orders:
            print(
                f"   - Order #{order.id}: {order.status} (Table: {order.table.table_number})")

        # Test permission classes
        print("\n3. Testing permission classes:")

        # Create a mock request
        class MockRequest:
            def __init__(self, user):
                self.user = user

        mock_request = MockRequest(chef)

        # Test chef permissions
        chef_perm = IsChefOrHigher()
        waiter_perm = IsWaiterOrHigher()
        cashier_perm = IsCashierOrHigher()

        print(
            f"   - IsChefOrHigher: {chef_perm.has_permission(mock_request, None)}")
        print(
            f"   - IsWaiterOrHigher: {waiter_perm.has_permission(mock_request, None)}")
        print(
            f"   - IsCashierOrHigher: {cashier_perm.has_permission(mock_request, None)}")

    except CustomUser.DoesNotExist:
        print("\nERROR: Test users not found. Run: python manage.py setup_dev_data")

    print("\n" + "=" * 60)
    print("RECOMMENDED ACTIONS:")
    print("=" * 60)
    print("1. Update OrderViewSet permission_classes to [IsAuthenticated]")
    print(
        "2. Update verify_token endpoint to use @permission_classes([AllowAny])")
    print("3. Run migrations if any changes made to models")
    print("4. Restart Django server")
    print("5. Clear browser cache and test again")


if __name__ == "__main__":
    check_permissions()
