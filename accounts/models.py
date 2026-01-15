from django.contrib.auth.models import AbstractUser
from django.db import models
from restaurants.models import Restaurant, Branch


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('chef', 'Chef'),
        ('waiter', 'Waiter'),
        ('cashier', 'Cashier'),
    ]

    # NEW: Manager scope choices
    MANAGER_SCOPE_CHOICES = [
        ('branch', 'Single Branch'),
        ('selected', 'Selected Branches'),
        ('restaurant', 'All Restaurant Branches'),
    ]

    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='waiter')

    # NEW: Manager scope field (only relevant for managers)
    manager_scope = models.CharField(
        max_length=20,
        choices=MANAGER_SCOPE_CHOICES,
        default='branch',
        blank=True,
        help_text="Data access scope for managers"
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff'
    )

    # NEW: For 'selected' scope managers
    managed_branches = models.ManyToManyField(
        Branch,
        blank=True,
        related_name='assigned_managers',
        help_text="Branches this manager can access (for 'selected' scope)"
    )

    phone = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(
        upload_to='profiles/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # NEW: Helper methods for scope management
    def get_accessible_branches(self):
        """
        Get all branches this user can access based on role and scope
        """
        if self.role == 'admin':
            # Admin can see all branches of their restaurant
            if self.restaurant:
                return Branch.objects.filter(restaurant=self.restaurant)
            return Branch.objects.none()

        if self.role != 'manager':
            # Non-managers only see their assigned branch
            if self.branch:
                return Branch.objects.filter(id=self.branch.id)
            return Branch.objects.none()

        # Manager scopes
        if self.manager_scope == 'branch' and self.branch:
            return Branch.objects.filter(id=self.branch.id)

        elif self.manager_scope == 'selected':
            # Return selected branches or default to user's branch
            if self.managed_branches.exists():
                return self.managed_branches.all()
            elif self.branch:
                return Branch.objects.filter(id=self.branch.id)

        elif self.manager_scope == 'restaurant' and self.restaurant:
            return self.restaurant.branches.all()

        return Branch.objects.none()

    def can_access_branch(self, branch):
        """
        Check if user can access specific branch
        """
        return branch in self.get_accessible_branches()

    def can_access_restaurant(self, restaurant):
        """
        Check if user can access specific restaurant
        """
        if self.role == 'admin':
            return True

        if self.role != 'manager':
            return restaurant == self.restaurant

        # Managers can access if it's their restaurant
        return restaurant == self.restaurant

    @property
    def effective_scope(self):
        """
        Get effective scope for data display purposes
        """
        if self.role != 'manager':
            return 'branch'  # Non-managers always see branch-level data

        return self.manager_scope
