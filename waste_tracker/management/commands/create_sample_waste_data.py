# waste_tracker/management/commands/create_sample_waste_data.py (FIXED VERSION)
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
    help = 'Create sample waste data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample waste data...')

        # Get or create restaurant and branch
        restaurant, _ = Restaurant.objects.get_or_create(
            name='Test Restaurant',
            defaults={'phone': '123-456-7890', 'address': '123 Test St.'}
        )

        branch, _ = Branch.objects.get_or_create(
            restaurant=restaurant,
            name='Branch 2',
            defaults={'location': 'Downtown', 'phone': '987-654-3210'}
        )

        # Create sample waste categories
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

        categories = {}
        for name, category_type, description, color in waste_categories:
            category, _ = WasteCategory.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                defaults={
                    'category_type': category_type,
                    'description': description,
                    'color_code': color
                }
            )
            categories[name] = category

        self.stdout.write(f'Created {len(waste_categories)} waste categories')

        # Create sample waste reasons
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

        all_reasons = []
        for category_name, reason_list in reasons_data.items():
            category = categories.get(category_name)
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
                all_reasons.append(reason)

        self.stdout.write(f'Created {len(all_reasons)} waste reasons')

        # Create sample stock items for Branch 2
        stock_items_data = [
            ('Chicken Breast', 'meat', 'kg', Decimal(
                '25.50'), Decimal('50'), Decimal('10')),
            ('Beef Sirloin', 'meat', 'kg', Decimal(
                '45.75'), Decimal('30'), Decimal('8')),
            ('Fresh Tomatoes', 'vegetable', 'kg', Decimal(
                '8.25'), Decimal('20'), Decimal('5')),
            ('Lettuce', 'vegetable', 'kg', Decimal(
                '6.50'), Decimal('15'), Decimal('4')),
            ('Potatoes', 'vegetable', 'kg', Decimal(
                '4.75'), Decimal('40'), Decimal('10')),
            ('Fresh Milk', 'dairy', 'l', Decimal(
                '3.25'), Decimal('20'), Decimal('5')),
            ('Cooking Oil', 'dry_goods', 'l', Decimal(
                '12.50'), Decimal('15'), Decimal('4')),
            ('Rice', 'dry_goods', 'kg', Decimal(
                '5.25'), Decimal('50'), Decimal('12')),
            ('Salt', 'spices', 'kg', Decimal('2.50'), Decimal('10'), Decimal('3')),
            ('Black Pepper', 'spices', 'kg', Decimal(
                '15.75'), Decimal('5'), Decimal('2')),
        ]

        stock_items = []
        for name, category, unit, cost, quantity, min_quantity in stock_items_data:
            stock_item, _ = StockItem.objects.get_or_create(
                restaurant=restaurant,
                branch=branch,
                name=name,
                defaults={
                    'category': category,
                    'unit': unit,
                    'cost_per_unit': cost,
                    'current_quantity': quantity,
                    'minimum_quantity': min_quantity,
                    'reorder_quantity': min_quantity * Decimal('1.5'),
                    'is_active': True
                }
            )
            stock_items.append(stock_item)

        self.stdout.write(
            f'Created {len(stock_items)} stock items for Branch 2')

        # Create sample waste records for the last 30 days
        self.stdout.write('Creating sample waste records...')

        # Get a user to record waste
        user = User.objects.filter(
            role__in=['chef', 'waiter', 'manager', 'admin']
        ).first()

        if not user:
            self.stdout.write('No users found. Creating a sample chef user...')
            user = User.objects.create_user(
                username='chef2',
                email='chef2@test.com',
                password='chef123',
                role='chef',
                restaurant=restaurant,
                branch=branch,
                first_name='Test',
                last_name='Chef'
            )

        # Create sample waste records for the last 30 days
        records_created = 0
        for days_ago in range(30):
            # Use timezone-aware datetime
            record_date = timezone.now() - timedelta(days=days_ago)

            # Create 0-3 waste records per day
            for _ in range(random.randint(0, 3)):
                if not all_reasons or not stock_items:
                    continue

                reason = random.choice(all_reasons)
                stock_item = random.choice(stock_items)

                # Generate random quantity (0.1 to 2.0) as Decimal
                quantity = Decimal(str(round(random.uniform(0.1, 2.0), 3)))

                # Calculate cost as Decimal
                total_cost = quantity * stock_item.cost_per_unit

                # Create linked stock transaction first
                transaction = StockTransaction.objects.create(
                    stock_item=stock_item,
                    transaction_type='waste',
                    quantity=quantity,
                    unit_cost=stock_item.cost_per_unit,
                    total_cost=total_cost,
                    reason=f'Waste: {reason.name}',
                    user=user,
                    restaurant=restaurant,
                    branch=branch,
                    transaction_date=record_date.date()
                )

                # Determine priority based on cost
                priority = 'medium'
                if total_cost > Decimal('50'):
                    priority = 'high'
                elif total_cost > Decimal('100'):
                    priority = 'critical'

                # Create waste record with timezone-aware datetime
                waste_record = WasteRecord.objects.create(
                    waste_reason=reason,
                    recorded_by=user,
                    branch=branch,
                    station=random.choice(
                        ['Grill', 'Fryer', 'Prep', 'Salad', 'Dessert', '']),
                    shift=random.choice(
                        ['morning', 'afternoon', 'evening', '']),
                    notes=f'Sample waste record for testing. Date: {record_date.date()}',
                    status='approved',
                    priority=priority,
                    recorded_at=record_date,
                    waste_occurred_at=record_date,
                    stock_transaction=transaction,
                    # Add waste_id explicitly
                    waste_id=uuid.uuid4()
                )

                records_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created sample waste data for {branch.name}. '
            f'Created {records_created} waste records.'
        ))
