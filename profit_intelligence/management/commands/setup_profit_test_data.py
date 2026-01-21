# setup_profit_test_data.py
from profit_intelligence.business_logic import ProfitCalculator
from restaurants.models import Restaurant, Branch
from accounts.models import CustomUser
from menu.models import MenuItem
from tables.models import Order, OrderItem
from datetime import date
from decimal import Decimal
from django.utils import timezone
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
django.setup()


def setup_profit_test_data():
    print("=== SETTING UP PROFIT TEST DATA ===\n")

    # 1. Get restaurant and branch
    restaurant = Restaurant.objects.first()
    branch = restaurant.branches.first()
    print(f"Restaurant: {restaurant.name}")
    print(f"Branch: {branch.name}\n")

    # 2. Set cost prices for menu items
    print("Setting cost prices for menu items...")
    for item in MenuItem.objects.all():
        # Set cost as 40% of price
        item.cost_price = item.price * Decimal('0.40')
        item.save()
        print(f"  ✓ {item.name}: ${item.price:.2f} → ${item.cost_price:.2f} cost")

    # 3. Create a completed order
    print("\nCreating completed order...")
    waiter = CustomUser.objects.filter(role='waiter').first()
    menu_items = MenuItem.objects.filter(is_available=True)[:3]

    order = Order.objects.create(
        order_number=f"TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        table=branch.tables.first(),
        waiter=waiter,
        order_type='waiter',
        status='completed',
        total_amount=Decimal('185.75'),
        subtotal=Decimal('150.00'),
        tax_amount=Decimal('22.50'),
        service_charge=Decimal('13.25'),
        discount_amount=Decimal('0.00'),
        is_paid=True,
        completed_at=timezone.now()
    )

    # Add items to order
    for item in menu_items:
        OrderItem.objects.create(
            order=order,
            menu_item=item,
            quantity=3,
            unit_price=item.price,
            special_instructions="Test order for profit dashboard"
        )

    print(f"  ✓ Order {order.order_number} created: ${order.total_amount:.2f}")
    print(f"  ✓ Added {len(menu_items)} items to order\n")

    # 4. Calculate profit
    today = date.today()
    print(f"Calculating profit for {today}...")
    result = ProfitCalculator.calculate_daily_profit(today, restaurant, branch)

    if result['success']:
        print(f"\n✅ PROFIT CALCULATION SUCCESSFUL!")
        print(f"   Revenue: ${result['revenue']:.2f}")
        print(f"   Cost: ${result['ingredient_cost']:.2f}")
        print(f"   Net Profit: ${result['net_profit']:.2f}")
        print(f"   Profit Margin: {result['profit_margin']:.1f}%")
        print(f"   Orders: {result['order_count']}")
    else:
        print(f"\n❌ ERROR: {result.get('error', 'Unknown')}")

    # 5. Check dashboard data
    print("\n=== DASHBOARD DATA CHECK ===")
    from profit_intelligence.models import ProfitAggregation
    agg = ProfitAggregation.objects.filter(
        date=today, restaurant=restaurant).first()
    if agg:
        print(f"Profit aggregation created:")
        print(f"  Date: {agg.date}")
        print(f"  Revenue: ${agg.revenue:.2f}")
        print(f"  Profit: ${agg.net_profit:.2f}")
        print(f"  Margin: {agg.profit_margin:.1f}%")
    else:
        print("No profit aggregation found!")

    print("\n✅ Setup complete! Now refresh your profit dashboard.")


if __name__ == "__main__":
    setup_profit_test_data()
