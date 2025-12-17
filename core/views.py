from django.shortcuts import render, redirect
import json
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django.utils import timezone
from django.db import connection
from django.core.cache import cache

from .serializers import HealthCheckSerializer
from accounts.permissions import IsAdminUser
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
@ensure_csrf_cookie
def login_page(request):
    """Render the login page"""
    return render(request, 'auth/login.html')


def landing_page(request):
    """Render the promotional landing page"""
    return render(request, 'landing/index.html')

# accounts/views.py - Add these views


@require_http_methods(["POST"])
def process_login(request):
    """Handle login form submission"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if user role matches selected role
            if hasattr(user, 'role') and user.role != role:
                return JsonResponse({
                    'error': f'User is not a {role}. Please select correct role.'
                }, status=403)

            # Login the user
            login(request, user)

            # Generate JWT tokens (if using JWT)
            from accounts.utils import generate_jwt_tokens
            tokens = generate_jwt_tokens(user)

            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'username': user.username,
                'role': user.role,
                **tokens
            })
        else:
            return JsonResponse({
                'error': 'Invalid username or password'
            }, status=401)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid request format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def process_logout(request):
    """Handle logout"""
    logout(request)
    return JsonResponse({
        'success': True,
        'message': 'Logged out successfully'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    # Check database connection
    try:
        connection.ensure_connection()
        database_status = 'connected'
    except Exception as e:
        database_status = f'error: {str(e)}'

    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        cache_status = 'connected' if cache.get(
            'health_check') == 'ok' else 'error'
    except Exception as e:
        cache_status = f'error: {str(e)}'

    data = {
        'status': 'healthy',
        'timestamp': timezone.now(),
        'database': database_status,
        'cache': cache_status,
        'service': 'restaurant-ordering-system',
        'version': '1.0.0'
    }

    serializer = HealthCheckSerializer(data)
    return Response(serializer.data)


class SystemInfoView(APIView):
    """System information endpoint (admin only)"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from django.conf import settings
        import platform
        import sys

        info = {
            'django_version': settings.VERSION,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'platform': platform.platform(),
            'debug_mode': settings.DEBUG,
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'timezone': str(settings.TIME_ZONE),
            'installed_apps_count': len(settings.INSTALLED_APPS),
            'middleware_count': len(settings.MIDDLEWARE),
        }

        return Response(info)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_stats(request):
    """System statistics (admin only)"""
    from accounts.models import CustomUser
    from restaurants.models import Restaurant, Branch
    from menu.models import Category, MenuItem

    stats = {
        'users': {
            'total': CustomUser.objects.count(),
            'admins': CustomUser.objects.filter(role='admin').count(),
            'managers': CustomUser.objects.filter(role='manager').count(),
            'chefs': CustomUser.objects.filter(role='chef').count(),
            'waiters': CustomUser.objects.filter(role='waiter').count(),
            'cashiers': CustomUser.objects.filter(role='cashier').count(),
            'active': CustomUser.objects.filter(is_active=True).count(),
        },
        'restaurants': {
            'total': Restaurant.objects.count(),
            'active': Restaurant.objects.filter(is_active=True).count(),
        },
        'branches': {
            'total': Branch.objects.count(),
            'active': Branch.objects.filter(is_active=True).count(),
        },
        'menu': {
            'categories': Category.objects.count(),
            'items': MenuItem.objects.count(),
            'available_items': MenuItem.objects.filter(is_available=True).count(),
        }
    }

    return Response(stats)
