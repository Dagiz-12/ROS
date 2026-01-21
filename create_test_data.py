#!/usr/bin/env python
"""
Quick test data creation script - FIXED VERSION
"""
import random
from tables.models import Table, Order, OrderItem
from menu.models import Category, MenuItem
from restaurants.models import Restaurant, Branch
from accounts.models import CustomUser
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Fix 1: Proper Django setup
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Fix 2: Set Django settings BEFORE importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')

try:
    django.setup()
except Exception as e:
    print(f"Django setup error: {e}")
    sys.exit(1)

# Now import Django models


def create_test_data():
    print("=== CREATING TEST DATA ===")

    # Check existing data first
    existing_orders = Order.objects.filter(status='completed').count()
    if existing_orders > 0:
        print(f"Found {existing_orders} existing completed orders")
        choice = input("Delete existing data and create fresh? (y/n): ")
        if choice.lower() != 'y':
            print("Keeping existing data")
            return

    # Get or create restaurant
    restaurant, created = Restaurant.objects.get_or_create(
        name="Ethiopian Feast Restaurant",
        defaults={
            'description': 'Authentic Ethiopian cuisine',
            'address': '123 Addis St, Addis Ababa',
            'phone': '+251911234567',
            'email': 'info@ethiopianfeast.com'
        }
    )
    print(
        f"Restaurant: {restaurant.name} {'(created)' if created else '(exists)'}")

    # Get or create branch
    branch, created = Branch.objects.get_or_create(
        restaurant=restaurant,
        name="Main Dining Hall",
        defaults={
            'location': 'Main Building, Ground Floor',
            'phone': '+251911234567'
        }
    )
    print(f"Branch: {branch.name} {'(created)' if created else '(exists)'}")

    # Get or create manager user (skip password if exists)
    try:
        manager_user = CustomUser.objects.get(username='manager1')
        print(f"Manager user exists: {manager_user.username}")
    except CustomUser.DoesNotExist:
        manager_user = CustomUser.objects.create(
            username='manager1',
            email='manager@ethiopianfeast.com',
            role='manager',
            restaurant=restaurant,
            branch=branch,
            is_active=True
        )
        manager_user.set_password('manager123')
        manager_user.save()
        print(f"Created manager user: {manager_user.username}")

    # Create Ethiopian menu categories
    categories = []
    category_data = [
        {'name': 'በርበሬ ምግቦች (Berbere Dishes)',
         'desc': 'Spicy berbere based dishes'},
        {'name': 'ጤፍ ምግቦች (Teff Dishes)',
         'desc': 'Traditional teff based dishes'},
        {'name': 'ሻምበል (Shambel)', 'desc': 'Sauces and stews'},
        {'name': 'መጠጥ (Drinks)', 'desc': 'Traditional drinks'},
    ]

    for i, cat_data in enumerate(category_data):
        cat, created = Category.objects.get_or_create(
            restaurant=restaurant,
            name=cat_data['name'],
            defaults={
                'description': cat_data['desc'],
                'order_index': i + 1
            }
        )
        categories.append(cat)
        print(f"Category: {cat.name} {'(created)' if created else '(exists)'}")

    # Create Ethiopian menu items
    menu_items = []
    item_data = [
        {'name': 'ዶሮ ወጥ (Doro Wat)', 'price': 250.00,
         'category': categories[0], 'cost': 80.00},
        {'name': 'ምስር ወጥ (Misir Wat)', 'price': 180.00,
         'category': categories[0], 'cost': 50.00},
        {'name': 'እንጀራ (Injera)', 'price': 50.00,
         'category': categories[1], 'cost': 15.00},
        {'name': 'ቲም ፈተሽ (Timatim Fitfit)', 'price': 120.00,
         'category': categories[2], 'cost': 30.00},
        {'name': 'ቡና (Coffee)', 'price': 40.00,
         'category': categories[3], 'cost': 10.00},
        {'name': 'ቶማ ሆም (Tomah Hom)', 'price': 60.00,
         'category': categories[3], 'cost': 15.00},
    ]

    for data in item_data:
        item, created = MenuItem.objects.get_or_create(
            category=data['category'],
            name=data['name'],
            defaults={
                'description': f'Traditional {data["name"]}',
                'price': Decimal(str(data['price'])),
                'cost_price': Decimal(str(data['cost'])),
                'profit_margin': ((data['price'] - data['cost']) / data['price']) * 100,
                'preparation_time': random.randint(10, 30),
                'is_available': True
            }
        )
        menu_items.append(item)
        print(
            f"Menu item: {data['name']} - ${data['price']} (${data['cost']} cost)")

    # Create tables
    tables = []
    for i in range(1, 11):
        table, created = Table.objects.get_or_create(
            branch=branch,
            table_number=i,
            defaults={
                'table_name': f'ጠረጴዛ {i}',
                'capacity': random.choice([2, 4, 6]),
                'status': 'available'
            }
        )
        tables.append(table)
        print(f"Table: {table.table_name} (Capacity: {table.capacity})")

    # Create completed orders for last 7 days
    today = datetime.now().date()
    total_orders_created = 0

    for days_ago in range(7):
        date = today - timedelta(days=days_ago)

        # Create 2-5 orders per day
        for order_num in range(random.randint(2, 5)):
            order = Order.objects.create(
                order_number=f"ETH-{date.strftime('%Y%m%d')}-{order_num+1:03d}",
                table=random.choice(tables),
                waiter=manager_user,
                customer_name=random.choice(
                    ['ተስፋዬ', 'ማርያም', 'ሀዋልት', 'ሰላም', 'ሀና']),
                order_type="waiter",
                status="completed",
                subtotal=Decimal('0.00'),
                tax_amount=Decimal('0.00'),
                total_amount=Decimal('0.00'),
                placed_at=datetime.combine(date, datetime.now(
                ).time()) - timedelta(hours=random.randint(1, 5)),
                confirmed_at=datetime.combine(date, datetime.now(
                ).time()) - timedelta(hours=random.randint(1, 4)),
                preparation_started_at=datetime.combine(
                    date, datetime.now().time()) - timedelta(hours=random.randint(1, 3)),
                ready_at=datetime.combine(date, datetime.now(
                ).time()) - timedelta(hours=random.randint(1, 2)),
                served_at=datetime.combine(
                    date, datetime.now().time()) - timedelta(hours=1),
                completed_at=datetime.combine(date, datetime.now().time()),
                is_paid=True
            )

            # Add 1-4 items to order
            total = Decimal('0.00')
            items_in_order = random.sample(menu_items, random.randint(1, 4))

            for item in items_in_order:
                quantity = random.randint(1, 3)
                OrderItem.objects.create(
                    order=order,
                    menu_item=item,
                    quantity=quantity,
                    unit_price=item.price
                )
                total += item.price * Decimal(str(quantity))

                # Update menu item sold count
                item.sold_count += quantity
                item.save()

            # Update order totals
            order.subtotal = total
            order.tax_amount = total * Decimal('0.15')
            order.total_amount = order.subtotal + order.tax_amount
            order.save()

            total_orders_created += 1
            print(
                f"Created order #{order.order_number} for {date}: ${order.total_amount:.2f}")

    print(f"\n=== TEST DATA SUMMARY ===")
    print(f"Restaurant: {restaurant.name}")
    print(f"Branch: {branch.name}")
    print(
        f"Categories: {Category.objects.filter(restaurant=restaurant).count()}")
    print(
        f"Menu Items: {MenuItem.objects.filter(category__restaurant=restaurant).count()}")
    print(f"Tables: {Table.objects.filter(branch=branch).count()}")
    print(f"Total Orders Created: {total_orders_created}")
    print(
        f"Completed Orders: {Order.objects.filter(status='completed').count()}")
    print(f"Order Items: {OrderItem.objects.count()}")

    # Calculate some stats
    total_revenue = Order.objects.filter(status='completed').aggregate(
        total=Sum('total_amount'))['total'] or Decimal('0.00')
    print(f"Total Revenue: ${total_revenue:.2f}")

    print(f"\n=== LOGIN CREDENTIALS ===")
    print(f"Manager Login:")
    print(f"  URL: http://localhost:8000/login/")
    print(f"  Username: manager1")
    print(f"  Password: manager123")
    print(f"  Restaurant: {restaurant.name}")

    print(f"\n=== ACCESS URLs ===")
    print(f"Admin Dashboard: http://localhost:8000/restaurant-admin/dashboard/")
    print(f"Profit Dashboard: http://localhost:8000/profit-intelligence/dashboard/")
    print(f"Waiter Interface: http://localhost:8000/waiter/dashboard/")


if __name__ == '__main__':
    create_test_data()
