# accounts/decorators.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def check_role(user, allowed_roles):
    """Check if user has one of the allowed roles"""
    return hasattr(user, 'role') and user.role in allowed_roles


def role_required(allowed_roles):
    """Decorator to check user role"""
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if not check_role(request.user, allowed_roles):
                return HttpResponseForbidden("Permission denied")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Specific role decorators for convenience
def admin_required(view_func):
    return role_required(['admin'])(view_func)


def manager_required(view_func):
    return role_required(['admin', 'manager'])(view_func)


def chef_required(view_func):
    return role_required(['admin', 'manager', 'chef'])(view_func)


def waiter_required(view_func):
    return role_required(['admin', 'manager', 'chef', 'waiter'])(view_func)


def cashier_required(view_func):
    return role_required(['admin', 'manager', 'chef', 'waiter', 'cashier'])(view_func)
