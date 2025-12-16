from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authentication import BasicAuthentication
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404

from .models import CustomUser
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    ChangePasswordSerializer, UpdateProfileSerializer,
    RoleAssignmentSerializer
)
from .utils import create_jwt_token, verify_jwt_token

# ============ Authentication Views ============


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login endpoint with JWT token generation"""
    serializer = LoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data['username']
    password = serializer.validated_data['password']

    # Try to authenticate user
    user = authenticate(request, username=username, password=password)

    if user is not None:
        if user.is_active:
            # Generate JWT token
            token = create_jwt_token(user)

            # Optionally perform Django login (for session-based auth if needed)
            django_login(request, user)

            return Response({
                'success': True,
                'message': 'Login successful',
                'token': token,
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Account is disabled'
            }, status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response({
            'success': False,
            'message': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint"""
    django_logout(request)
    return Response({
        'success': True,
        'message': 'Logged out successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """User registration endpoint"""
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Generate token for auto-login after registration
        token = create_jwt_token(user)

        return Response({
            'success': True,
            'message': 'User registered successfully',
            'token': token,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============ User Profile Views ============


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Get current user's profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """Update user profile"""
    serializer = UpdateProfileSerializer(
        request.user, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Change user password"""
    serializer = ChangePasswordSerializer(data=request.data)

    if serializer.is_valid():
        user = request.user

        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'success': False,
                'message': 'Old password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Update session to prevent logout
        update_session_auth_hash(request, user)

        return Response({
            'success': True,
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============ Admin Views ============


@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_list_view(request):
    """Admin: List all users (with pagination)"""
    users = CustomUser.objects.all().order_by('-date_joined')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def assign_role_view(request):
    """Admin: Assign/change user role"""
    serializer = RoleAssignmentSerializer(data=request.data)

    if serializer.is_valid():
        user_id = serializer.validated_data['user_id']
        new_role = serializer.validated_data['role']

        try:
            user = CustomUser.objects.get(id=user_id)

            # Prevent admin from removing their own admin role
            if user == request.user and new_role != 'admin':
                return Response({
                    'success': False,
                    'message': 'Cannot remove admin role from yourself'
                }, status=status.HTTP_400_BAD_REQUEST)

            user.role = new_role
            user.save()

            return Response({
                'success': True,
                'message': f'Role updated to {new_role}',
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def toggle_user_status(request, user_id):
    """Admin: Activate/Deactivate user"""
    try:
        user = CustomUser.objects.get(id=user_id)

        # Prevent deactivating self
        if user == request.user:
            return Response({
                'success': False,
                'message': 'Cannot deactivate yourself'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = not user.is_active
        user.save()

        status_text = 'activated' if user.is_active else 'deactivated'

        return Response({
            'success': True,
            'message': f'User {status_text} successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)

    except CustomUser.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

# ============ JWT Authentication View ============


class JWTAuthenticationView(APIView):
    """Verify JWT token and return user info"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

            # Verify token
            payload = verify_jwt_token(token)

            if payload:
                user_id = payload.get('user_id')
                try:
                    user = CustomUser.objects.get(id=user_id)
                    return Response({
                        'valid': True,
                        'user': UserSerializer(user).data
                    })
                except CustomUser.DoesNotExist:
                    return Response({
                        'valid': False,
                        'message': 'User not found'
                    }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'valid': False,
            'message': 'Invalid token'
        }, status=status.HTTP_401_UNAUTHORIZED)
