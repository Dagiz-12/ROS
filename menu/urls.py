from django.urls import path, include
from rest_framework.routers import DefaultRouter
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
