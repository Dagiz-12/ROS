from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'restaurants', views.RestaurantViewSet, basename='restaurant')
router.register(r'branches', views.BranchViewSet, basename='branch')
router.register(r'my-restaurant', views.MyRestaurantView,
                basename='my-restaurant')
router.register(r'my-branch', views.MyBranchView, basename='my-branch')

urlpatterns = [
    path('', include(router.urls)),
]
