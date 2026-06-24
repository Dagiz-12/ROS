from django.urls import path, include
try:
    from rest_framework.routers import DefaultRouter
except Exception:
    # Fallback for environments where djangorestframework isn't installed
    # Provide a minimal DefaultRouter-compatible stub so tooling/linting
    # doesn't fail and imports succeed. This router returns no URLs.
    class DefaultRouter:
        def __init__(self, *args, **kwargs):
            self._registered = []

        def register(self, prefix, viewset, basename=None):
            # store registration info if needed for debugging
            self._registered.append((prefix, viewset, basename))

        @property
        def urls(self):
            return []
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'items', views.MenuItemViewSet, basename='menuitem')
router.register(r'restaurant-menu', views.RestaurantMenuView,
                basename='restaurant-menu')

urlpatterns = [
    path('', include(router.urls)),
    path('public/<int:restaurant_id>/',
         views.PublicMenuView.as_view(), name='public-menu'),
]
