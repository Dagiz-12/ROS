from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('system/info/', views.SystemInfoView.as_view(), name='system-info'),
    path('system/stats/', views.system_stats, name='system-stats'),
]
