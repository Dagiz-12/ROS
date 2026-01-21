# test_database_queries.py
from profit_intelligence.business_logic import ProfitCalculator
from restaurants.models import Restaurant
import os
import django
import sys
from django.db import connection
from django.utils import timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
django.setup()


def test_query_performance():
    print("=== DATABASE QUERY PERFORMANCE ===")

    restaurant = Restaurant.objects.get(name="Ethiopian Feast Restaurant")
    today = timezone.now().date()

    # Enable query logging
    from django.db import reset_queries
    from django.conf import settings

    settings.DEBUG = True
    reset_queries()

    print("\n1. Testing Profit Calculation Queries...")

    # Run profit calculation
    profit_data = ProfitCalculator.calculate_daily_profit(
        date=today,
        restaurant=restaurant
    )

    # Analyze queries
    queries = connection.queries
    print(f"Total Queries: {len(queries)}")

    # Group by model
    query_types = {}
    for query in queries:
        sql = query['sql'].lower()
        if 'select' in sql:
            if 'order' in sql:
                key = 'Order'
            elif 'menu' in sql:
                key = 'MenuItem'
            elif 'profit' in sql:
                key = 'Profit'
            elif 'waste' in sql:
                key = 'Waste'
            else:
                key = 'Other'
        else:
            key = 'Write'

        query_types[key] = query_types.get(key, 0) + 1

    print("\nQuery Breakdown:")
    for model, count in query_types.items():
        print(f"  {model}: {count} queries")

    # Check for N+1 problems
    print("\n2. Checking for N+1 Problems...")
    for i, query in enumerate(queries[:20]):  # First 20 queries
        print(f"  Query {i+1}: {query['sql'][:100]}...")

    # Recommendations
    print("\n=== OPTIMIZATION RECOMMENDATIONS ===")
    if query_types.get('Order', 0) > 5:
        print("⚠️  Multiple Order queries detected - Consider using select_related/prefetch_related")

    if len(queries) > 20:
        print("⚠️  High query count - Consider caching or batch operations")

    settings.DEBUG = False


if __name__ == '__main__':
    test_query_performance()
