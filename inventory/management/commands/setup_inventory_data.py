# inventory/management/commands/setup_inventory_data.py
from django.core.management.base import BaseCommand
from inventory.models import StockItem, Recipe
from menu.models import MenuItem
from restaurants.models import Restaurant
import random


class Command(BaseCommand):
    help = 'Setup sample inventory data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up sample inventory data...')

        # Get first restaurant
        restaurant = Restaurant.objects.first()
        if not restaurant:
            self.stdout.write(self.style.ERROR(
                'No restaurant found. Please run setup_dev_data first.'))
            return

        # Sample inventory items for a restaurant
        stock_items_data = [
            # Meat & Poultry
            {'name': 'Chicken Breast', 'category': 'meat', 'unit': 'kg',
                'current_quantity': 10.0, 'minimum_quantity': 2.0, 'cost_per_unit': 5.50},
            {'name': 'Beef Steak', 'category': 'meat', 'unit': 'kg',
                'current_quantity': 8.0, 'minimum_quantity': 2.0, 'cost_per_unit': 12.00},
            {'name': 'Ground Beef', 'category': 'meat', 'unit': 'kg',
                'current_quantity': 15.0, 'minimum_quantity': 3.0, 'cost_per_unit': 8.00},

            # Vegetables
            {'name': 'Potatoes', 'category': 'vegetable', 'unit': 'kg',
                'current_quantity': 20.0, 'minimum_quantity': 5.0, 'cost_per_unit': 1.50},
            {'name': 'Onions', 'category': 'vegetable', 'unit': 'kg',
                'current_quantity': 10.0, 'minimum_quantity': 2.0, 'cost_per_unit': 1.00},
            {'name': 'Tomatoes', 'category': 'vegetable', 'unit': 'kg',
                'current_quantity': 15.0, 'minimum_quantity': 3.0, 'cost_per_unit': 2.00},
            {'name': 'Lettuce', 'category': 'vegetable', 'unit': 'unit',
                'current_quantity': 50.0, 'minimum_quantity': 10.0, 'cost_per_unit': 0.50},

            # Dairy
            {'name': 'Milk', 'category': 'dairy', 'unit': 'l',
                'current_quantity': 20.0, 'minimum_quantity': 5.0, 'cost_per_unit': 1.20},
            {'name': 'Cheese', 'category': 'dairy', 'unit': 'kg',
                'current_quantity': 8.0, 'minimum_quantity': 2.0, 'cost_per_unit': 6.00},
            {'name': 'Butter', 'category': 'dairy', 'unit': 'kg',
                'current_quantity': 5.0, 'minimum_quantity': 1.0, 'cost_per_unit': 4.00},

            # Dry Goods
            {'name': 'Rice', 'category': 'dry_goods', 'unit': 'kg',
                'current_quantity': 25.0, 'minimum_quantity': 5.0, 'cost_per_unit': 2.00},
            {'name': 'Pasta', 'category': 'dry_goods', 'unit': 'kg',
                'current_quantity': 15.0, 'minimum_quantity': 3.0, 'cost_per_unit': 1.80},
            {'name': 'Flour', 'category': 'dry_goods', 'unit': 'kg',
                'current_quantity': 20.0, 'minimum_quantity': 5.0, 'cost_per_unit': 1.00},

            # Beverages
            {'name': 'Coffee Beans', 'category': 'beverage', 'unit': 'kg',
                'current_quantity': 10.0, 'minimum_quantity': 2.0, 'cost_per_unit': 8.00},
            {'name': 'Tea Leaves', 'category': 'beverage', 'unit': 'kg',
                'current_quantity': 5.0, 'minimum_quantity': 1.0, 'cost_per_unit': 6.00},
            {'name': 'Sugar', 'category': 'beverage', 'unit': 'kg',
                'current_quantity': 15.0, 'minimum_quantity': 3.0, 'cost_per_unit': 1.50},
        ]

        # Create stock items
        stock_items = []
        for item_data in stock_items_data:
            stock_item, created = StockItem.objects.get_or_create(
                name=item_data['name'],
                restaurant=restaurant,
                defaults={
                    'category': item_data['category'],
                    'unit': item_data['unit'],
                    'current_quantity': item_data['current_quantity'],
                    'minimum_quantity': item_data['minimum_quantity'],
                    'cost_per_unit': item_data['cost_per_unit'],
                    # 50% more than minimum
                    'reorder_quantity': item_data['minimum_quantity'] * 1.5,
                    'supplier': 'Main Supplier',
                    'is_active': True,
                }
            )
            stock_items.append(stock_item)
            if created:
                self.stdout.write(f"Created stock item: {stock_item.name}")

        # Create sample recipes for menu items
        menu_items = MenuItem.objects.filter(category__restaurant=restaurant)

        sample_recipes = [
            # For a burger
            {'menu_item_name': 'Classic Burger', 'ingredients': [
                ('Beef Steak', 0.2),  # 200g beef
                ('Lettuce', 0.05),    # 50g lettuce
                ('Tomatoes', 0.05),   # 50g tomatoes
                ('Onions', 0.03),     # 30g onions
                ('Cheese', 0.05),     # 50g cheese
            ]},
            # For pasta
            {'menu_item_name': 'Spaghetti Bolognese', 'ingredients': [
                ('Ground Beef', 0.15),  # 150g beef
                ('Pasta', 0.2),         # 200g pasta
                ('Tomatoes', 0.1),      # 100g tomatoes
                ('Onions', 0.05),       # 50g onions
            ]},
            # For coffee
            {'menu_item_name': 'Coffee', 'ingredients': [
                ('Coffee Beans', 0.02),  # 20g coffee beans
                ('Sugar', 0.01),         # 10g sugar
                ('Milk', 0.1),           # 100ml milk
            ]},
        ]

        for recipe_data in sample_recipes:
            try:
                menu_item = MenuItem.objects.get(
                    name=recipe_data['menu_item_name'], category__restaurant=restaurant)

                for ingredient_name, quantity in recipe_data['ingredients']:
                    stock_item = StockItem.objects.get(
                        name=ingredient_name, restaurant=restaurant)

                    Recipe.objects.get_or_create(
                        menu_item=menu_item,
                        stock_item=stock_item,
                        defaults={
                            'quantity_required': quantity,
                            # 5-15% waste
                            'waste_factor': random.uniform(5, 15),
                        }
                    )

                self.stdout.write(f"Created recipes for: {menu_item.name}")
            except MenuItem.DoesNotExist:
                continue
            except StockItem.DoesNotExist:
                continue

        self.stdout.write(self.style.SUCCESS(
            'Successfully setup sample inventory data!'))
