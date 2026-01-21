# check_data.py
from profit_intelligence.models import ProfitAggregation
from datetime import datetime
from waste_tracker.models import WasteRecord
from tables.models import Order
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
django.setup()


print("=== DATA DIAGNOSTIC ===")

# Check orders
total_orders = Order.objects.count()
completed_orders = Order.objects.filter(status='completed').count()
print(f"Total Orders: {total_orders}")
print(f"Completed Orders: {completed_orders}")

if completed_orders > 0:
    print("\nRecent Completed Orders:")
    for order in Order.objects.filter(status='completed')[:5]:
        print(
            f"  Order #{order.order_number}: ${order.total_amount} - {order.placed_at.date()}")

# Check waste records
waste_records = WasteRecord.objects.count()
print(f"\nTotal Waste Records: {waste_records}")

if waste_records > 0:
    print("\nRecent Waste Records:")
    for waste in WasteRecord.objects.all()[:5]:
        print(
            f"  {waste.stock_item.name if waste.stock_item else 'Unknown'}: ${waste.total_cost}")

# Check if profit calculations have data
profit_records = ProfitAggregation.objects.count()
print(f"\nProfit Aggregation Records: {profit_records}")

if profit_records > 0:
    print("\nRecent Profit Records:")
    for profit in ProfitAggregation.objects.all()[:5]:
        print(
            f"  {profit.date}: Revenue ${profit.total_revenue}, Profit ${profit.net_profit}")
