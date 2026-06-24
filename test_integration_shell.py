# test_integration_shell.py
print("🧪 Copy and paste this code into Django shell:")
print("=" * 60)

shell_code = '''
# Run in Django shell: python manage.py shell

import sys
from django.utils import timezone
from decimal import Decimal

print("🧪 Testing Payment → Inventory Integration")
print("=" * 60)

# 1. Check system status
from accounts.models import CustomUser
from restaurants.models import Restaurant, Branch
from menu.models import MenuItem
from tables.models import Table, Order, OrderItem
from inventory.models import StockItem, Recipe, StockTransaction
from waste_tracker.models import WasteRecord, WasteReason
from payments.models import Payment

print("📊 System Status Check:")
print(f"   Restaurants: {Restaurant.objects.count()}")
print(f"   Menu Items: {MenuItem.objects.filter(is_available=True).count()}")
print(f"   Recipes: {Recipe.objects.count()}")
print(f"   Stock Items: {StockItem.objects.count()}")
print(f"   Orders: {Order.objects.count()}")
print(f"   Completed Orders: {Order.objects.filter(status='completed').count()}")
print(f"   Payments: {Payment.objects.count()}")

# 2. Test inventory deduction on order completion
print("\\n🔍 Testing Inventory Deduction on Order Completion...")

# Get a completed order
completed_order = Order.objects.filter(status='completed', inventory_deducted=False).first()

if completed_order:
    print(f"✅ Found order #{completed_order.order_number}")
    print(f"   Items: {completed_order.items.count()}")
    
    # Check if inventory should be deducted
    for item in completed_order.items.all():
        print(f"   - {item.quantity}x {item.menu_item.name}")
        
        # Check recipes
        recipes = Recipe.objects.filter(menu_item=item.menu_item)
        for recipe in recipes:
            print(f"     Uses: {recipe.quantity_required} {recipe.stock_item.unit} of {recipe.stock_item.name}")
            
        # Check StockTransactions
        transactions = StockTransaction.objects.filter(
            reference_type='order',
            reference_id=completed_order.id
        )
        print(f"     Stock Transactions: {transactions.count()}")
        
        if transactions.exists():
            for t in transactions:
                print(f"       {t.transaction_type}: {t.quantity_change} {t.stock_item.unit}")
        else:
            print("     ❌ No stock transactions found!")
else:
    print("⚠️  No completed orders found or all have inventory deducted")

# 3. Test waste recording
print("\\n🗑️  Testing Waste Recording...")

waste_records = WasteRecord.objects.filter(status='approved')[:3]
if waste_records:
    for waste in waste_records:
        print(f"✅ Waste Record: {waste.quantity} {waste.unit} of {waste.stock_item.name}")
        print(f"   Reason: {waste.waste_reason.name}")
        
        # Check StockTransactions
        transactions = StockTransaction.objects.filter(
            reference_type='waste',
            reference_id=waste.id
        )
        print(f"   Stock Transactions: {transactions.count()}")
else:
    print("⚠️  No approved waste records found")

# 4. Check for inconsistencies
print("\\n🔧 Checking for Inconsistencies...")

# Orders completed but not inventory deducted
inconsistent_orders = Order.objects.filter(
    status='completed',
    inventory_deducted=False
).count()
print(f"   Orders completed but inventory not deducted: {inconsistent_orders}")

# Stock items with negative quantity
negative_stock = StockItem.objects.filter(current_quantity__lt=0).count()
print(f"   Stock items with negative quantity: {negative_stock}")

# Missing recipes
menu_items_no_recipe = MenuItem.objects.filter(is_available=True).exclude(
    id__in=Recipe.objects.values('menu_item')
).count()
print(f"   Menu items without recipes: {menu_items_no_recipe}")

print("\\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

# Quick fix suggestions
if inconsistent_orders > 0:
    print("\\n🚨 ACTION REQUIRED:")
    print("   Run this command to fix inventory deduction:")
    print("   from tables.models import Order")
    print("   for order in Order.objects.filter(status='completed', inventory_deducted=False):")
    print("       order.complete_order()  # Or trigger inventory deduction")

if negative_stock > 0:
    print("\\n⚠️  WARNING: Some stock items have negative quantities!")
    print("   Check StockTransaction records for errors.")
'''

print(shell_code)
print("\nTo run: python manage.py shell")
print("Then copy and paste the code above")
