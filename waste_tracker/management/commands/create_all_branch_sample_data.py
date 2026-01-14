# waste_tracker/management/commands/create_all_branch_sample_data.py
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
    help = 'Create sample waste data for ALL branches'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample waste data for ALL branches...')

        # Get or create restaurant
        restaurant, _ = Restaurant.objects.get_or_create(
            name='Test Restaurant',
            defaults={'phone': '123-456-7890', 'address': '123 Test St.'}
        )

        # Get or create branches
        branches_data = [
            ('Main Branch', 'Downtown', '111-111-1111'),
            ('Branch 2', 'Uptown', '222-222-2222'),
            ('Branch 3', 'Westside', '333-333-3333'),
            ('Branch 4', 'Eastside', '444-444-4444'),
        ]

        branches = []
        for name, location, phone in branches_data:
            branch, created = Branch.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                defaults={'location': location, 'phone': phone}
            )
            branches.append(branch)
            if created:
                self.stdout.write(f'Created branch: {name}')

        self.stdout.write(f'Working with {len(branches)} branches')

        # Create waste categories (restaurant-wide)
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

        # Create waste reasons for each category
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

        # Create users for each branch
        users_by_branch = {}
        for branch in branches:
            # Create a chef user for this branch
            username = f'chef_{branch.name.lower().replace(" ", "_")}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@test.com',
                    'password': 'chef123',
                    'role': 'chef',
                    'restaurant': restaurant,
                    'branch': branch,
                    'first_name': 'Test',
                    'last_name': f'Chef {branch.name}'
                }
            )
            users_by_branch[branch.id] = user
            if created:
                self.stdout.write(
                    f'Created user: {username} for {branch.name}')

        # Create stock items for EACH branch
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

        stock_items_by_branch = {}
        for branch in branches:
            branch_items = []
            for name, category, unit, cost, quantity, min_quantity in stock_items_data:
                stock_item, created = StockItem.objects.get_or_create(
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
                branch_items.append(stock_item)
            stock_items_by_branch[branch.id] = branch_items

        self.stdout.write(f'Created stock items for {len(branches)} branches')

        # Create sample waste records for each branch
        total_records = 0
        for branch in branches:
            branch_records = 0
            user = users_by_branch.get(branch.id)
            stock_items = stock_items_by_branch.get(branch.id, [])

            if not user or not stock_items:
                continue

            # Create 5-15 waste records per branch
            for _ in range(random.randint(5, 15)):
                reason = random.choice(all_reasons)
                stock_item = random.choice(stock_items)

                # Generate random quantity (0.1 to 2.0) as Decimal
                quantity = Decimal(str(round(random.uniform(0.1, 2.0), 3)))

                # Calculate cost as Decimal
                total_cost = quantity * stock_item.cost_per_unit

                # Random date in last 30 days
                days_ago = random.randint(0, 30)
                record_date = timezone.now() - timedelta(days=days_ago)

                # Create linked stock transaction
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

                # Determine priority
                priority = 'medium'
                if total_cost > Decimal('50'):
                    priority = 'high'
                elif total_cost > Decimal('100'):
                    priority = 'critical'

                # Create waste record
                WasteRecord.objects.create(
                    waste_reason=reason,
                    recorded_by=user,
                    branch=branch,
                    station=random.choice(
                        ['Grill', 'Fryer', 'Prep', 'Salad', 'Dessert', '']),
                    shift=random.choice(
                        ['morning', 'afternoon', 'evening', '']),
                    notes=f'Sample waste record for {branch.name}. Date: {record_date.date()}',
                    status='approved',
                    priority=priority,
                    recorded_at=record_date,
                    waste_occurred_at=record_date,
                    stock_transaction=transaction,
                    waste_id=uuid.uuid4()
                )

                branch_records += 1
                total_records += 1

            self.stdout.write(
                f'  {branch.name}: {branch_records} waste records')

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully created sample data!\n'
            f'   - Restaurant: {restaurant.name}\n'
            f'   - Branches: {len(branches)}\n'
            f'   - Waste categories: {len(categories)}\n'
            f'   - Waste reasons: {len(all_reasons)}\n'
            f'   - Total waste records: {total_records}\n'
            f'\nTest users created (password: chef123):\n'
        ))

        for branch in branches:
            user = users_by_branch.get(branch.id)
            if user:
                self.stdout.write(
                    f'   - {user.username} (Branch: {branch.name})')

        self.stdout.write('\n📝 Notes:')
        self.stdout.write('   1. All users have password: "chef123"')
        self.stdout.write('   2. Waste records are from last 30 days')
        self.stdout.write('   3. Stock items created for each branch')
        self.stdout.write('   4. Use any branch user to test waste entry')
