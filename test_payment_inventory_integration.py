# test_payment_inventory_integration.py
from decimal import Decimal
from django.utils import timezone
from payments.models import Payment
from waste_tracker.models import WasteRecord, WasteReason
from inventory.models import StockItem, Recipe
from tables.models import Table, Order, OrderItem, Cart, CartItem
from menu.models import MenuItem, Category
from restaurants.models import Restaurant, Branch
from accounts.models import CustomUser
import os
import django
import sys

from django.db import models

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_system.settings')
django.setup()


def test_complete_inventory_flow():
    """Test the complete flow from order to inventory deduction"""
    print("=" * 60)
    print("TESTING: Payment → Inventory Deduction Integration")
    print("=" * 60)

    try:
        # 1. Get test restaurant and branch
        restaurant = Restaurant.objects.first()
        branch = Branch.objects.first()

        if not restaurant or not branch:
            print("❌ No restaurant or branch found. Run setup_dev_data first.")
            return False

        print(f"✅ Using restaurant: {restaurant.name}")
        print(f"✅ Using branch: {branch.name}")

        # 2. Get a menu item with recipe
        menu_items = MenuItem.objects.filter(is_available=True)
        if not menu_items:
            print("❌ No menu items available")
            return False

        menu_item = menu_items.first()
        print(
            f"✅ Testing with menu item: {menu_item.name} (${menu_item.price})")

        # 3. Check if menu item has recipe
        recipes = Recipe.objects.filter(menu_item=menu_item)
        if not recipes:
            print("⚠️  Menu item has no recipe. Creating sample recipe...")

            # Get or create sample stock items
            chicken = StockItem.objects.filter(
                name__icontains='chicken').first()
            if not chicken:
                chicken = StockItem.objects.create(
                    name='Chicken Breast',
                    restaurant=restaurant,
                    branch=branch,
                    unit='kg',
                    current_quantity=Decimal('10.0'),
                    unit_cost=Decimal('200.0')
                )

            # Create recipe
            recipe = Recipe.objects.create(
                menu_item=menu_item,
                stock_item=chicken,
                quantity_required=Decimal('0.2'),  # 200g per serving
                waste_factor=Decimal('0.05')  # 5% waste
            )
            print(f"✅ Created recipe: {recipe}")
        else:
            recipe = recipes.first()
            print(f"✅ Found existing recipe: {recipe}")
            print(
                f"   Uses: {recipe.quantity_required} {recipe.stock_item.unit} of {recipe.stock_item.name}")

        # 4. Check current stock levels
        stock_item = recipe.stock_item
        initial_stock = stock_item.current_quantity
        print(
            f"📊 Initial stock of {stock_item.name}: {initial_stock} {stock_item.unit}")

        # 5. Create a test order
        waiter = CustomUser.objects.filter(role='waiter').first()
        table = Table.objects.filter(branch=branch).first()

        if not waiter or not table:
            print("❌ No waiter or table found")
            return False

        print(f"✅ Using waiter: {waiter.username}")
        print(f"✅ Using table: {table.table_number}")

        # Create order
        order = Order.objects.create(
            order_number=Order.generate_order_number(),
            table=table,
            waiter=waiter,
            customer_name="Test Customer",
            order_type='waiter',
            status='confirmed',
            subtotal=menu_item.price,
            tax_amount=Decimal('0.0'),
            total_amount=menu_item.price
        )

        # Add order item
        order_item = OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=2,
            unit_price=menu_item.price
        )

        print(
            f"✅ Created order #{order.order_number} with {order_item.quantity} x {menu_item.name}")

        # 6. Simulate order preparation (kitchen workflow)
        print("\n🔧 Simulating kitchen workflow...")
        order.status = 'preparing'
        order.save()
        print(f"   Order status: {order.status}")

        order.status = 'ready'
        order.save()
        print(f"   Order status: {order.status}")

        # 7. Simulate serving
        order.status = 'served'
        order.save()
        print(f"   Order status: {order.status}")
        print("   ✅ Order is now ready for payment")

        # 8. Create payment
        payment = Payment.objects.create(
            order=order,
            payment_method='cash',
            amount=order.total_amount,
            status='completed',
            processed_by=waiter
        )

        print(f"💰 Created payment #{payment.payment_id}")
        print(f"   Amount: ${payment.amount}")
        print(f"   Method: {payment.payment_method}")

        # 9. Complete order (should trigger inventory deduction)
        order.status = 'completed'
        order.is_paid = True
        order.save()

        print(f"\n✅ Order #{order.order_number} marked as completed")
        print(f"   Order is_paid: {order.is_paid}")
        print(f"   Order inventory_deducted: {order.inventory_deducted}")

        # 10. Check if inventory was deducted
        stock_item.refresh_from_db()
        final_stock = stock_item.current_quantity

        print(f"\n📊 Stock after order completion:")
        print(f"   {stock_item.name}: {final_stock} {stock_item.unit}")
        print(f"   Change: {initial_stock - final_stock} {stock_item.unit}")

        # 11. Check StockTransaction was created
        from inventory.models import StockTransaction
        transactions = StockTransaction.objects.filter(
            stock_item=stock_item,
            reference_type='order',
            reference_id=order.id
        )

        if transactions.exists():
            print(f"✅ StockTransaction created for order deduction")
            for t in transactions:
                print(
                    f"   Transaction: {t.transaction_type} - {t.quantity_change} {stock_item.unit}")
        else:
            print("❌ No StockTransaction created for order")

        # 12. Verify calculations
        expected_deduction = recipe.quantity_required * \
            order_item.quantity * (1 + recipe.waste_factor)
        actual_deduction = initial_stock - final_stock

        print(f"\n🧮 Verification:")
        print(f"   Expected deduction: {expected_deduction} {stock_item.unit}")
        print(f"   Actual deduction: {actual_deduction} {stock_item.unit}")
        print(
            f"   Match: {abs(expected_deduction - actual_deduction) < Decimal('0.01')}")

        return True

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_waste_inventory_deduction():
    """Test waste recording → inventory deduction"""
    print("\n" + "=" * 60)
    print("TESTING: Waste Recording → Inventory Deduction")
    print("=" * 60)

    try:
        # Get test data
        restaurant = Restaurant.objects.first()
        branch = Branch.objects.first()
        chef = CustomUser.objects.filter(role='chef').first()

        if not chef:
            print("❌ No chef user found")
            return False

        # Get a stock item
        stock_item = StockItem.objects.filter(
            restaurant=restaurant,
            branch=branch,
            current_quantity__gt=Decimal('1.0')
        ).first()

        if not stock_item:
            print("❌ No stock items with quantity > 0")
            return False

        initial_stock = stock_item.current_quantity
        print(f"📊 Testing waste deduction for: {stock_item.name}")
        print(f"   Initial quantity: {initial_stock} {stock_item.unit}")

        # Get waste reason
        waste_reason = WasteReason.objects.first()
        if not waste_reason:
            waste_reason = WasteReason.objects.create(
                name='Spoilage',
                category_id=1,
                controllability='controllable'
            )

        # Create waste record
        waste_record = WasteRecord.objects.create(
            stock_item=stock_item,
            waste_reason=waste_reason,
            quantity=Decimal('0.5'),
            unit=stock_item.unit,
            recorded_by=chef,
            branch=branch,
            station='Prep',
            status='approved'
        )

        print(
            f"🗑️  Created waste record: {waste_record.quantity} {stock_item.unit}")
        print(f"   Reason: {waste_reason.name}")
        print(f"   Status: {waste_record.status}")

        # Check if stock was deducted
        stock_item.refresh_from_db()
        final_stock = stock_item.current_quantity

        print(f"\n📊 Stock after waste recording:")
        print(f"   {stock_item.name}: {final_stock} {stock_item.unit}")
        print(f"   Change: {initial_stock - final_stock} {stock_item.unit}")

        # Check StockTransaction
        from inventory.models import StockTransaction
        transactions = StockTransaction.objects.filter(
            stock_item=stock_item,
            reference_type='waste',
            reference_id=waste_record.id
        )

        if transactions.exists():
            print(f"✅ StockTransaction created for waste")
            for t in transactions:
                print(
                    f"   Transaction: {t.transaction_type} - {t.quantity_change} {stock_item.unit}")
        else:
            print("❌ No StockTransaction created for waste")

        return True

    except Exception as e:
        print(f"❌ Error during waste test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_system_status():
    """Check overall system status"""
    print("\n" + "=" * 60)
    print("SYSTEM STATUS CHECK")
    print("=" * 60)

    # Count objects
    from django.db.models import Count

    print(f"📊 Database Counts:")
    print(f"   Restaurants: {Restaurant.objects.count()}")
    print(f"   Menu Items: {MenuItem.objects.count()}")
    print(f"   Recipes: {Recipe.objects.count()}")
    print(f"   Stock Items: {StockItem.objects.count()}")
    print(f"   Orders: {Order.objects.count()}")
    print(f"   Payments: {Payment.objects.count()}")
    print(f"   Waste Records: {WasteRecord.objects.count()}")

    # Check for orders needing inventory deduction
    orders_needing_deduction = Order.objects.filter(
        status='completed',
        inventory_deducted=False
    ).count()

    print(
        f"\n🔍 Orders needing inventory deduction: {orders_needing_deduction}")

    if orders_needing_deduction > 0:
        print("⚠️  Some completed orders haven't deducted inventory!")

    # Check low stock items
    low_stock_items = StockItem.objects.filter(
        current_quantity__lt=models.F('minimum_quantity')
    ).count()

    print(f"📉 Low stock items (< minimum): {low_stock_items}")

    return True


if __name__ == "__main__":
    print("🧪 Starting Integration Tests...")
    print()

    # Run tests
    test1 = test_complete_inventory_flow()
    test2 = test_waste_inventory_deduction()
    check_system_status()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Order → Inventory Flow: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Waste → Inventory Flow: {'✅ PASS' if test2 else '❌ FAIL'}")

    if test1 and test2:
        print("\n🎉 All integration tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check above for details.")
