from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    path('profile/change-password/',
         views.change_password_view, name='change_password'),

    # Admin Functions
    path('users/', views.user_list_view, name='user_list'),
    path('assign-role/', views.assign_role_view, name='assign_role'),
    path('toggle-user/<int:user_id>/',
         views.toggle_user_status, name='toggle_user_status'),

    # JWT Verification
    path('verify-token/', views.JWTAuthenticationView.as_view(), name='verify_token'),
]
