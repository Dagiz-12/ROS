from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from restaurants.models import Restaurant, Branch


class Command(BaseCommand):
    help = 'Create initial development data'

    def handle(self, *args, **kwargs):
        # Create a demo restaurant
        restaurant, created = Restaurant.objects.get_or_create(
            name="Demo Restaurant",
            defaults={
                'description': "A demo restaurant for development",
                'address': "123 Main Street",
                'phone': "+251911223344",
                'email': "demo@restaurant.com"
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created demo restaurant'))

        # Create a branch
        branch, created = Branch.objects.get_or_create(
            restaurant=restaurant,
            name="Main Branch",
            defaults={
                'location': "Ground Floor",
                'phone': "+251911223345"
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created main branch'))

        # Create admin user if not exists
        admin_user, created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@restaurant.com',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True
            }
        )

        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(
                'Created admin user (password: admin123)'))

        self.stdout.write(self.style.SUCCESS('Initial data setup complete!'))
