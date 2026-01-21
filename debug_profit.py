# debug_profit.py
from datetime import date
from restaurants.models import Restaurant
from profit_intelligence.business_logic import ProfitCalculator
from profit_intelligence.models import ProfitAggregation
import os
import django
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
django.setup()


def debug_profit_system():
    print("=== PROFIT INTELLIGENCE DEBUGGING ===\n")

    # 1. Check if any restaurants exist
    restaurants = Restaurant.objects.all()
    print(f"1. Restaurants in system: {restaurants.count()}")
    for r in restaurants:
        print(f"   - {r.name} (ID: {r.id})")

    # 2. Check profit aggregations
    aggregations = ProfitAggregation.objects.all()
    print(f"\n2. Profit aggregations: {aggregations.count()}")
    if aggregations.count() > 0:
        for agg in aggregations.order_by('-date')[:5]:
            print(
                f"   - {agg.date}: ${agg.revenue:.2f} revenue, ${agg.net_profit:.2f} profit")

    # 3. Test profit calculation for today
    print("\n3. Testing today's profit calculation...")
    if restaurants.exists():
        restaurant = restaurants.first()
        today = date.today()

        print(f"   Calculating profit for {restaurant.name} on {today}...")
        result = ProfitCalculator.calculate_daily_profit(today, restaurant)

        if result.get('success'):
            print(
                f"   ✓ Success! Revenue: ${result['revenue']:.2f}, Profit: ${result['net_profit']:.2f}")
        else:
            print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")

    # 4. Check URL patterns
    print("\n4. URL Patterns for profit intelligence:")
    try:
        from profit_intelligence.urls import urlpatterns
        for pattern in urlpatterns:
            print(f"   - {pattern.pattern}")
    except Exception as e:
        print(f"   Error checking URLs: {e}")

    print("\n=== DEBUGGING COMPLETE ===")


if __name__ == "__main__":
    debug_profit_system()
