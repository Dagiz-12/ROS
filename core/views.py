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
