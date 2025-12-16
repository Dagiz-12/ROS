from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin users"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsManagerOrAdmin(permissions.BasePermission):
    """Allow access to managers and admins"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager']


class IsChefOrHigher(permissions.BasePermission):
    """Allow access to chef, manager, and admin"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager', 'chef']


class IsWaiterOrHigher(permissions.BasePermission):
    """Allow access to waiter, chef, manager, and admin"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager', 'chef', 'waiter']


class IsCashierOrHigher(permissions.BasePermission):
    """Allow access to cashier and above"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager', 'chef', 'waiter', 'cashier']
