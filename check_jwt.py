# check_jwt.py
from accounts.utils import create_jwt_token, verify_jwt_token
from accounts.models import CustomUser
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()


def check_jwt_functions():
    """Check if JWT functions work"""
    print("=" * 60)
    print("CHECKING JWT FUNCTIONS")
    print("=" * 60)

    try:
        # Get a test user
        user = CustomUser.objects.first()
        if user:
            print(f"\n1. Testing with user: {user.username} (ID: {user.id})")

            # Create token
            token = create_jwt_token(user)
            print(f"   ✅ Token created: {token[:50]}...")

            # Verify token
            payload = verify_jwt_token(token)
            if payload:
                print(f"   ✅ Token verified successfully")
                print(f"   Payload: {payload}")
            else:
                print(f"   ❌ Token verification failed")
        else:
            print(f"\n❌ No users in database")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_jwt_functions()
