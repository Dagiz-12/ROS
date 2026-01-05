# accounts/authentication.py - Create this file
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from .utils import verify_jwt_token

User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    """JWT authentication for DRF"""

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return None  # Let other auth classes try

        try:
            token = auth_header.split(' ')[1]
            payload = verify_jwt_token(token)

            if not payload:
                raise AuthenticationFailed('Invalid or expired token')

            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Invalid token payload')

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found')

            # Check if user is active
            if not user.is_active:
                raise AuthenticationFailed('User account is disabled')

            return (user, token)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication error: {str(e)}')
