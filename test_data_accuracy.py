# test_data_accuracy.py
from django.utils import timezone
from profit_intelligence.business_logic import ProfitCalculator
from profit_intelligence.models import ProfitAggregation
from tables.models import Order, OrderItem
from restaurants.models import Restaurant
import os
import django
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
django.setup()


def test_profit_calculations():
    print("=== PROFIT CALCULATIONS VALIDATION ===")

    # Get Ethiopian Feast Restaurant
    restaurant = Restaurant.objects.get(name="Ethiopian Feast Restaurant")
    today = timezone.now().date()

    # Manual calculation
    orders = Order.objects.filter(
        table__branch__restaurant=restaurant,
        status='completed',
        completed_at__date=today
    )

    manual_revenue = sum(order.total_amount for order in orders)
    manual_orders = orders.count()

    print(f"Manual Calculation:")
    print(f"  Orders: {manual_orders}")
    print(f"  Revenue: ${manual_revenue:.2f}")

    # System calculation
    profit_data = ProfitCalculator.calculate_daily_profit(
        date=today,
        restaurant=restaurant
    )

    print(f"\nSystem Calculation:")
    print(f"  Orders: {profit_data.order_count}")
    print(f"  Revenue: ${profit_data.revenue:.2f}")
    print(f"  Net Profit: ${profit_data.net_profit:.2f}")
    print(f"  Profit Margin: {profit_data.profit_margin:.1f}%")

    # Verify
    if abs(float(manual_revenue) - float(profit_data.revenue)) < 0.01:
        print("✅ Revenue calculation is ACCURATE")
    else:
        print(
            f"❌ Revenue MISMATCH: Manual ${manual_revenue:.2f} vs System ${profit_data.revenue:.2f}")

    # Check profit aggregation
    aggregation = ProfitAggregation.objects.filter(
        date=today,
        restaurant=restaurant
    ).first()

    if aggregation:
        print(f"\nProfit Aggregation Record:")
        print(f"  Revenue: ${aggregation.revenue:.2f}")
        print(f"  Net Profit: ${aggregation.net_profit:.2f}")
        print(f"  Margin: {aggregation.profit_margin:.1f}%")

        if abs(float(profit_data.revenue) - float(aggregation.revenue)) < 0.01:
            print("✅ Aggregation matches calculation")
        else:
            print("❌ Aggregation mismatch")

    return manual_revenue, profit_data.revenue


if __name__ == '__main__':
    test_profit_calculations()
