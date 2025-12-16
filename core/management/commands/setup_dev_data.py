from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from restaurants.models import Restaurant, Branch
from menu.models import Category, MenuItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup development data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Setting up development data...'))

        # Create a demo restaurant
        restaurant, created = Restaurant.objects.get_or_create(
            name="Ethiopian Feast Restaurant",
            defaults={
                'description': "Authentic Ethiopian cuisine with modern service",
                'address': "Bole Road, Addis Ababa, Ethiopia",
                'phone': "+251111223344",
                'email': "info@ethiopianfeast.com",
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created restaurant: {restaurant.name}'))

        # Create main branch
        branch, created = Branch.objects.get_or_create(
            restaurant=restaurant,
            name="Main Dining Hall",
            defaults={
                'location': "Ground Floor, Building A",
                'phone': "+251111223345",
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created branch: {branch.name}'))

        # Create users with different roles
        users_data = [
            {'username': 'admin', 'email': 'admin@restaurant.com',
                'role': 'admin', 'password': 'admin123'},
            {'username': 'manager1', 'email': 'manager@restaurant.com',
                'role': 'manager', 'password': 'manager123'},
            {'username': 'chef1', 'email': 'chef@restaurant.com',
                'role': 'chef', 'password': 'chef123'},
            {'username': 'waiter1', 'email': 'waiter@restaurant.com',
                'role': 'waiter', 'password': 'waiter123'},
            {'username': 'cashier1', 'email': 'cashier@restaurant.com',
                'role': 'cashier', 'password': 'cashier123'},
        ]

        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'role': user_data['role'],
                    'restaurant': restaurant,
                    'branch': branch if user_data['role'] in ['chef', 'waiter', 'cashier'] else None
                }
            )

            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f'Created user: {user.username} ({user.role})'))

        # Create menu categories
        categories_data = [
            {'name': 'Appetizers', 'order_index': 1},
            {'name': 'Main Courses', 'order_index': 2},
            {'name': 'Vegetarian Dishes', 'order_index': 3},
            {'name': 'Drinks', 'order_index': 4},
            {'name': 'Desserts', 'order_index': 5},
        ]

        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                restaurant=restaurant,
                name=cat_data['name'],
                defaults={
                    'order_index': cat_data['order_index'],
                    'is_active': True
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'Created category: {category.name}'))

        # Create menu items
        menu_items_data = [
            # Appetizers
            {'category': 'Appetizers', 'name': 'Samosa',
                'price': 50, 'preparation_time': 10},
            {'category': 'Appetizers', 'name': 'Spring Rolls',
                'price': 60, 'preparation_time': 12},
            {'category': 'Appetizers', 'name': 'Chicken Wings',
                'price': 120, 'preparation_time': 15},

            # Main Courses
            {'category': 'Main Courses', 'name': 'Doro Wot',
                'price': 250, 'preparation_time': 30},
            {'category': 'Main Courses', 'name': 'Key Wot',
                'price': 220, 'preparation_time': 25},
            {'category': 'Main Courses', 'name': 'Tibs',
                'price': 280, 'preparation_time': 20},

            # Vegetarian
            {'category': 'Vegetarian Dishes', 'name': 'Shiro',
                'price': 150, 'preparation_time': 15},
            {'category': 'Vegetarian Dishes', 'name': 'Misir Wot',
                'price': 140, 'preparation_time': 20},
            {'category': 'Vegetarian Dishes', 'name': 'Gomen',
                'price': 130, 'preparation_time': 15},

            # Drinks
            {'category': 'Drinks', 'name': 'Coffee',
                'price': 30, 'preparation_time': 5},
            {'category': 'Drinks', 'name': 'Tea',
                'price': 20, 'preparation_time': 5},
            {'category': 'Drinks', 'name': 'Fresh Juice',
                'price': 80, 'preparation_time': 8},

            # Desserts
            {'category': 'Desserts', 'name': 'Cake',
                'price': 100, 'preparation_time': 10},
            {'category': 'Desserts', 'name': 'Ice Cream',
                'price': 70, 'preparation_time': 5},
        ]

        for item_data in menu_items_data:
            category = Category.objects.get(
                restaurant=restaurant, name=item_data['category'])

            item, created = MenuItem.objects.get_or_create(
                category=category,
                name=item_data['name'],
                defaults={
                    'price': item_data['price'],
                    'preparation_time': item_data['preparation_time'],
                    'is_available': True,
                    'description': f"Delicious {item_data['name']} prepared fresh"
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'Created menu item: {item.name} - ${item.price}'))

        self.stdout.write(self.style.SUCCESS(
            'Development data setup complete!'))
        self.stdout.write(self.style.WARNING('\nTest Credentials:'))
        self.stdout.write('Admin: admin / admin123')
        self.stdout.write('Manager: manager1 / manager123')
        self.stdout.write('Chef: chef1 / chef123')
        self.stdout.write('Waiter: waiter1 / waiter123')
        self.stdout.write('Cashier: cashier1 / cashier123')
