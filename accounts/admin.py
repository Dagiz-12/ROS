# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    # Fields to display in list view
    list_display = ('username', 'email', 'role', 'restaurant',
                    'branch', 'is_active', 'date_joined')

    # Filter options
    list_filter = ('role', 'is_active', 'restaurant', 'branch', 'is_staff')

    # Search fields
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')

    # Fields to display in detail view
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name',
         'last_name', 'email', 'phone', 'profile_image')}),
        (_('Restaurant Info'), {'fields': ('restaurant', 'branch', 'role')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Fields for add form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role',
                       'restaurant', 'branch', 'is_active', 'is_staff'),
        }),
    )

    # Ordering
    ordering = ('-date_joined',)

    # Actions
    actions = ['activate_users', 'deactivate_users',
               'make_chef', 'make_waiter', 'make_cashier']

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} users activated.")
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        # Don't allow deactivating superusers
        queryset.filter(is_superuser=False).update(is_active=False)
        count = queryset.filter(is_superuser=False).count()
        self.message_user(request, f"{count} users deactivated.")
    deactivate_users.short_description = "Deactivate selected users"

    def make_chef(self, request, queryset):
        queryset.update(role='chef')
        self.message_user(request, f"{queryset.count()} users set as Chef.")
    make_chef.short_description = "Set as Chef"

    def make_waiter(self, request, queryset):
        queryset.update(role='waiter')
        self.message_user(request, f"{queryset.count()} users set as Waiter.")
    make_waiter.short_description = "Set as Waiter"

    def make_cashier(self, request, queryset):
        queryset.update(role='cashier')
        self.message_user(request, f"{queryset.count()} users set as Cashier.")
    make_cashier.short_description = "Set as Cashier"


# Register the model
admin.site.register(CustomUser, CustomUserAdmin)
