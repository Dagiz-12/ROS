# check_users.py
from django.contrib.auth.hashers import make_password, check_password
from accounts.models import CustomUser
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()


def check_test_users():
    """Check if test users exist in database"""
    print("=" * 60)
    print("CHECKING TEST USERS IN DATABASE")
    print("=" * 60)

    test_users = [
        ('admin', 'admin123', 'admin'),
        ('waiter1', 'waiter123', 'waiter'),
        ('chef1', 'chef123', 'chef'),
        ('cashier1', 'cashier123', 'cashier'),
        ('manager1', 'manager123', 'manager')
    ]

    all_users = CustomUser.objects.all()
    print(f"Total users in database: {all_users.count()}\n")

    for username, password, expected_role in test_users:
        try:
            user = CustomUser.objects.get(username=username)

            # Check password
            password_valid = user.check_password(password)

            # Check role
            role_correct = user.role == expected_role

            # Check active status
            is_active = user.is_active

            status_icon = "✅" if (
                password_valid and role_correct and is_active) else "❌"

            print(f"{status_icon} {username}:")
            print(
                f"   Role: {user.role} (expected: {expected_role}) {'✅' if role_correct else '❌'}")
            print(f"   Password valid: {'✅' if password_valid else '❌'}")
            print(f"   Active: {'✅' if is_active else '❌'}")
            print(f"   Email: {user.email}")

        except CustomUser.DoesNotExist:
            print(f"❌ {username}: NOT FOUND IN DATABASE")

    print("\n" + "=" * 60)
    print("ALL USERS IN DATABASE:")
    print("=" * 60)
    for user in all_users:
        print(f"{user.id}: {user.username} - {user.role} - Active: {user.is_active}")


if __name__ == "__main__":
    check_test_users()
