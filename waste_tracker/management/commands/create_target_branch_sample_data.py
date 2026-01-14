# waste_tracker/management/commands/create_target_branch_sample_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from restaurants.models import Restaurant, Branch
from inventory.models import StockItem, StockTransaction
from waste_tracker.models import WasteCategory, WasteReason, WasteRecord
from decimal import Decimal
import random
import uuid
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample waste data for Main Dining Hall and Main Branch'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample waste data for target branches...')

        # Find or create the specific restaurants and branches
        try:
            # Ethiopian Feast Restaurant
            ethiopian_restaurant = Restaurant.objects.get(
                name='Ethiopian Feast Restaurant')
            self.stdout.write(f'Found restaurant: {ethiopian_restaurant.name}')
        except Restaurant.DoesNotExist:
            ethiopian_restaurant = Restaurant.objects.create(
                name='Ethiopian Feast Restaurant',
                phone='111-222-3333',
                address='123 Ethiopian St.',
                description='Authentic Ethiopian cuisine'
            )
            self.stdout.write(
                f'Created restaurant: {ethiopian_restaurant.name}')

        try:
            # Main Dining Hall branch
            main_dining = Branch.objects.get(
                restaurant=ethiopian_restaurant,
                name='Main Dining Hall'
            )
            self.stdout.write(f'Found branch: {main_dining.name}')
        except Branch.DoesNotExist:
            main_dining = Branch.objects.create(
                restaurant=ethiopian_restaurant,
                name='Main Dining Hall',
                location='Ground Floor',
                phone='111-222-3333',
                settings={'tables': 20, 'capacity': 100}
            )
            self.stdout.write(f'Created branch: {main_dining.name}')

        try:
            # Demo Restaurant
            demo_restaurant = Restaurant.objects.get(name='Demo Restaurant')
            self.stdout.write(f'Found restaurant: {demo_restaurant.name}')
        except Restaurant.DoesNotExist:
            demo_restaurant = Restaurant.objects.create(
                name='Demo Restaurant',
                phone='444-555-6666',
                address='456 Demo St.',
                description='Demo restaurant for testing'
            )
            self.stdout.write(f'Created restaurant: {demo_restaurant.name}')

        try:
            # Main Branch
            main_branch = Branch.objects.get(
                restaurant=demo_restaurant,
                name='Main Branch'
            )
            self.stdout.write(f'Found branch: {main_branch.name}')
        except Branch.DoesNotExist:
            main_branch = Branch.objects.create(
                restaurant=demo_restaurant,
                name='Main Branch',
                location='Main Street',
                phone='444-555-6666',
                settings={'tables': 15, 'capacity': 75}
            )
            self.stdout.write(f'Created branch: {main_branch.name}')

        branches = [main_dining, main_branch]

        # Create waste categories for BOTH restaurants
        waste_categories = [
            ('Spoilage', 'spoilage', 'Food that spoiled or expired', '#ef4444'),
            ('Preparation', 'preparation',
             'Waste during food preparation', '#f59e0b'),
            ('Overproduction', 'overproduction',
             'Food prepared but not sold', '#8b5cf6'),
            ('Customer Returns', 'customer_return',
             'Food returned by customers', '#ec4899'),
            ('Portion Control', 'portion_control',
             'Incorrect portion sizes', '#10b981'),
        ]

        # Create categories for Ethiopian restaurant
        ethiopian_categories = {}
        for name, category_type, description, color in waste_categories:
            category, _ = WasteCategory.objects.get_or_create(
                restaurant=ethiopian_restaurant,
                name=name,
                defaults={
                    'category_type': category_type,
                    'description': description,
                    'color_code': color
                }
            )
            ethiopian_categories[name] = category

        # Create categories for Demo restaurant
        demo_categories = {}
        for name, category_type, description, color in waste_categories:
            category, _ = WasteCategory.objects.get_or_create(
                restaurant=demo_restaurant,
                name=name,
                defaults={
                    'category_type': category_type,
                    'description': description,
                    'color_code': color
                }
            )
            demo_categories[name] = category

        self.stdout.write(f'Created waste categories for both restaurants')

        # Create waste reasons
        reasons_data = {
            'Spoilage': [
                ('Expired', 'Item passed expiration date', 'uncontrollable'),
                ('Improper Storage', 'Stored at wrong temperature', 'controllable'),
                ('Damaged Packaging', 'Packaging damaged during delivery',
                 'partially_controllable'),
            ],
            'Preparation': [
                ('Over-trimming', 'Excessive trimming of vegetables/meat', 'controllable'),
                ('Spillage', 'Spilled during preparation', 'controllable'),
                ('Burned', 'Food burned during cooking', 'controllable'),
            ],
            'Overproduction': [
                ('Overestimated Demand', 'Prepared more than needed', 'controllable'),
                ('Slow Day', 'Fewer customers than expected', 'uncontrollable'),
                ('Event Cancelled', 'Catering event cancelled', 'uncontrollable'),
            ],
            'Customer Returns': [
                ('Wrong Order', 'Wrong item served', 'controllable'),
                ('Not Satisfied', 'Customer not satisfied with food',
                 'partially_controllable'),
                ('Allergy Concern', 'Customer had allergy concerns', 'controllable'),
            ],
            'Portion Control': [
                ('Over-portioned', 'Served too large portions', 'controllable'),
                ('Inconsistent', 'Portion sizes inconsistent', 'controllable'),
                ('Training Issue', 'Staff not properly trained', 'controllable'),
            ],
        }

        # Create reasons for Ethiopian restaurant
        ethiopian_reasons = []
        for category_name, reason_list in reasons_data.items():
            category = ethiopian_categories.get(category_name)
            if not category:
                continue

            for reason_name, description, controllability in reason_list:
                reason, _ = WasteReason.objects.get_or_create(
                    category=category,
                    name=reason_name,
                    defaults={
                        'description': description,
                        'controllability': controllability,
                        'requires_explanation': controllability == 'controllable'
                    }
                )
                ethiopian_reasons.append(reason)

        # Create reasons for Demo restaurant
        demo_reasons = []
        for category_name, reason_list in reasons_data.items():
            category = demo_categories.get(category_name)
            if not category:
                continue

            for reason_name, description, controllability in reason_list:
                reason, _ = WasteReason.objects.get_or_create(
                    category=category,
                    name=reason_name,
                    defaults={
                        'description': description,
                        'controllability': controllability,
                        'requires_explanation': controllability == 'controllable'
                    }
                )
                demo_reasons.append(reason)

        self.stdout.write(
            f'Created {len(ethiopian_reasons)} waste reasons for Ethiopian Feast')
        self.stdout.write(
            f'Created {len(demo_reasons)} waste reasons for Demo Restaurant')

        # Create stock items for Main Dining Hall (Ethiopian Feast)
        ethiopian_stock_items = [
            # Ethiopian-specific items
            ('Injera', 'dry_goods', 'kg', Decimal(
                '8.50'), Decimal('30'), Decimal('10')),
            ('Berbere Spice', 'spices', 'kg', Decimal(
                '25.75'), Decimal('5'), Decimal('2')),
            ('Teff Flour', 'dry_goods', 'kg', Decimal(
                '12.50'), Decimal('20'), Decimal('5')),
            ('Niter Kibbeh', 'dairy', 'kg', Decimal(
                '18.25'), Decimal('10'), Decimal('3')),
            ('Shiro Powder', 'dry_goods', 'kg', Decimal(
                '15.00'), Decimal('8'), Decimal('2')),
            # General items
            ('Chicken', 'meat', 'kg', Decimal('22.50'), Decimal('25'), Decimal('8')),
            ('Beef', 'meat', 'kg', Decimal('38.75'), Decimal('20'), Decimal('6')),
            ('Lentils', 'vegetable', 'kg', Decimal(
                '6.25'), Decimal('15'), Decimal('5')),
            ('Onions', 'vegetable', 'kg', Decimal(
                '4.50'), Decimal('20'), Decimal('6')),
            ('Tomatoes', 'vegetable', 'kg', Decimal(
                '7.25'), Decimal('18'), Decimal('5')),
        ]

        self.stdout.write(f'\nCreating stock items for Main Dining Hall...')
        ethiopian_items = []
        for name, category, unit, cost, quantity, min_quantity in ethiopian_stock_items:
            stock_item, created = StockItem.objects.get_or_create(
                restaurant=ethiopian_restaurant,
                branch=main_dining,
                name=name,
                defaults={
                    'category': category,
                    'unit': unit,
                    'cost_per_unit': cost,
                    'current_quantity': quantity,
                    'minimum_quantity': min_quantity,
                    'reorder_quantity': min_quantity * Decimal('1.5'),
                    'is_active': True,
                    'description': f'Ethiopian cuisine ingredient - {name}'
                }
            )
            ethiopian_items.append(stock_item)
            if created:
                self.stdout.write(f'  ✓ {name} ({quantity} {unit})')

        # Create stock items for Main Branch (Demo Restaurant)
        demo_stock_items = [
            # General restaurant items
            ('Chicken Breast', 'meat', 'kg', Decimal(
                '24.50'), Decimal('40'), Decimal('12')),
            ('Beef Sirloin', 'meat', 'kg', Decimal(
                '42.75'), Decimal('30'), Decimal('10')),
            ('Salmon Fillet', 'seafood', 'kg', Decimal(
                '35.50'), Decimal('15'), Decimal('5')),
            ('Mixed Vegetables', 'vegetable', 'kg', Decimal(
                '8.75'), Decimal('25'), Decimal('8')),
            ('Pasta', 'dry_goods', 'kg', Decimal(
                '6.25'), Decimal('20'), Decimal('6')),
            ('Rice', 'dry_goods', 'kg', Decimal(
                '5.50'), Decimal('30'), Decimal('10')),
            ('Olive Oil', 'dry_goods', 'l', Decimal(
                '14.25'), Decimal('10'), Decimal('3')),
            ('Fresh Herbs', 'spices', 'kg', Decimal(
                '28.50'), Decimal('3'), Decimal('1')),
            ('Cheese', 'dairy', 'kg', Decimal('16.75'), Decimal('12'), Decimal('4')),
            ('Cream', 'dairy', 'l', Decimal('8.25'), Decimal('15'), Decimal('5')),
        ]

        self.stdout.write(f'\nCreating stock items for Main Branch...')
        demo_items = []
        for name, category, unit, cost, quantity, min_quantity in demo_stock_items:
            stock_item, created = StockItem.objects.get_or_create(
                restaurant=demo_restaurant,
                branch=main_branch,
                name=name,
                defaults={
                    'category': category,
                    'unit': unit,
                    'cost_per_unit': cost,
                    'current_quantity': quantity,
                    'minimum_quantity': min_quantity,
                    'reorder_quantity': min_quantity * Decimal('1.5'),
                    'is_active': True,
                    'description': f'Demo restaurant item - {name}'
                }
            )
            demo_items.append(stock_item)
            if created:
                self.stdout.write(f'  ✓ {name} ({quantity} {unit})')

        # Get or create users for each branch
        self.stdout.write(f'\nSetting up users...')

        # For Main Dining Hall
        ethiopian_user = User.objects.filter(
            restaurant=ethiopian_restaurant,
            branch=main_dining,
            role__in=['chef', 'waiter', 'manager']
        ).first()

        if not ethiopian_user:
            ethiopian_user = User.objects.create_user(
                username='chef_ethiopian',
                email='chef@ethiopianfeast.com',
                password='chef123',
                role='chef',
                restaurant=ethiopian_restaurant,
                branch=main_dining,
                first_name='Ethiopian',
                last_name='Chef'
            )
            self.stdout.write(
                f'  Created user: chef_ethiopian for Main Dining Hall')

        # For Main Branch
        demo_user = User.objects.filter(
            restaurant=demo_restaurant,
            branch=main_branch,
            role__in=['chef', 'waiter', 'manager']
        ).first()

        if not demo_user:
            demo_user = User.objects.create_user(
                username='chef_demo',
                email='chef@demorestaurant.com',
                password='chef123',
                role='chef',
                restaurant=demo_restaurant,
                branch=main_branch,
                first_name='Demo',
                last_name='Chef'
            )
            self.stdout.write(f'  Created user: chef_demo for Main Branch')

        # Create sample waste records
        self.stdout.write(f'\nCreating sample waste records...')

        # For Main Dining Hall
        ethiopian_records = 0
        for _ in range(random.randint(8, 12)):
            reason = random.choice(ethiopian_reasons)
            stock_item = random.choice(ethiopian_items)

            quantity = Decimal(str(round(random.uniform(0.2, 1.5), 3)))
            total_cost = quantity * stock_item.cost_per_unit

            days_ago = random.randint(0, 30)
            record_date = timezone.now() - timedelta(days=days_ago)

            # Create transaction
            transaction = StockTransaction.objects.create(
                stock_item=stock_item,
                transaction_type='waste',
                quantity=quantity,
                unit_cost=stock_item.cost_per_unit,
                total_cost=total_cost,
                reason=f'Waste: {reason.name}',
                user=ethiopian_user,
                restaurant=ethiopian_restaurant,
                branch=main_dining,
                transaction_date=record_date.date()
            )

            # Create waste record
            WasteRecord.objects.create(
                waste_reason=reason,
                recorded_by=ethiopian_user,
                branch=main_dining,
                station=random.choice(
                    ['Injera Station', 'Stew Station', 'Prep', 'Grill']),
                shift=random.choice(['morning', 'afternoon', 'evening']),
                notes=f'Sample waste at Ethiopian Feast. Item: {stock_item.name}',
                status='approved',
                priority='medium' if total_cost < Decimal('40') else 'high',
                recorded_at=record_date,
                waste_occurred_at=record_date,
                stock_transaction=transaction,
                waste_id=uuid.uuid4()
            )
            ethiopian_records += 1

        # For Main Branch
        demo_records = 0
        for _ in range(random.randint(10, 15)):
            reason = random.choice(demo_reasons)
            stock_item = random.choice(demo_items)

            quantity = Decimal(str(round(random.uniform(0.1, 2.0), 3)))
            total_cost = quantity * stock_item.cost_per_unit

            days_ago = random.randint(0, 30)
            record_date = timezone.now() - timedelta(days=days_ago)

            # Create transaction
            transaction = StockTransaction.objects.create(
                stock_item=stock_item,
                transaction_type='waste',
                quantity=quantity,
                unit_cost=stock_item.cost_per_unit,
                total_cost=total_cost,
                reason=f'Waste: {reason.name}',
                user=demo_user,
                restaurant=demo_restaurant,
                branch=main_branch,
                transaction_date=record_date.date()
            )

            # Create waste record
            WasteRecord.objects.create(
                waste_reason=reason,
                recorded_by=demo_user,
                branch=main_branch,
                station=random.choice(
                    ['Grill', 'Fryer', 'Prep', 'Salad', 'Dessert']),
                shift=random.choice(['morning', 'afternoon', 'evening']),
                notes=f'Sample waste at Demo Restaurant. Item: {stock_item.name}',
                status='approved',
                priority='medium' if total_cost < Decimal('50') else 'high',
                recorded_at=record_date,
                waste_occurred_at=record_date,
                stock_transaction=transaction,
                waste_id=uuid.uuid4()
            )
            demo_records += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ SUCCESS! Created sample data for both branches:\n\n'
            f'ETHIOPIAN FEAST RESTAURANT:\n'
            f'  • Restaurant: {ethiopian_restaurant.name}\n'
            f'  • Branch: {main_dining.name}\n'
            f'  • Stock items: {len(ethiopian_items)}\n'
            f'  • Waste records: {ethiopian_records}\n'
            f'  • Test user: chef_ethiopian (password: chef123)\n\n'
            f'DEMO RESTAURANT:\n'
            f'  • Restaurant: {demo_restaurant.name}\n'
            f'  • Branch: {main_branch.name}\n'
            f'  • Stock items: {len(demo_items)}\n'
            f'  • Waste records: {demo_records}\n'
            f'  • Test user: chef_demo (password: chef123)\n\n'
            f'📝 TO TEST:\n'
            f'  1. Login as chef_ethiopian to see Ethiopian stock items\n'
            f'  2. Login as chef_demo to see Demo Restaurant stock items\n'
            f'  3. Both users can access waste entry at /waste/entry/\n'
            f'  4. Waste dashboards at /waste/dashboard/'
        ))
