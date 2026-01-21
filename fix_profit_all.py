# fix_profit_all.py
import logging
from django.db import connection
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
django.setup()


logger = logging.getLogger(__name__)


def fix_database_tables():
    """Fix profit_intelligence database tables"""
    print("🔧 FIXING DATABASE TABLES...")

    try:
        with connection.cursor() as cursor:
            # Check current table structure
            cursor.execute(
                "PRAGMA table_info(profit_intelligence_profitaggregation)")
            columns = [col[1] for col in cursor.fetchall()]
            print("Current ProfitAggregation columns:", columns)

            # Add missing columns if needed
            if 'level' not in columns:
                print("Adding 'level' column...")
                cursor.execute("""
                    ALTER TABLE profit_intelligence_profitaggregation
                    ADD COLUMN level VARCHAR(20) DEFAULT 'daily'
                """)

            if 'aggregation_id' not in columns:
                print("Adding 'aggregation_id' column...")
                cursor.execute("""
                    ALTER TABLE profit_intelligence_profitaggregation
                    ADD COLUMN aggregation_id VARCHAR(36)
                """)

            print("✅ Database tables fixed")

    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False

    return True


def fix_api_views():
    """Fix the API views to use proper Django request handling"""
    print("\n🔧 FIXING API VIEWS...")

    # Update the api_views.py file
    api_views_path = 'profit_intelligence/api_views.py'

    with open(api_views_path, 'r') as f:
        content = f.read()

    # Replace request.query_params with request.GET
    fixed_content = content.replace('request.query_params', 'request.GET')

    with open(api_views_path, 'w') as f:
        f.write(fixed_content)

    print("✅ API views fixed")
    return True


def calculate_profits():
    """Calculate and save profit data"""
    print("\n💰 CALCULATING PROFITS...")

    try:
        from restaurants.models import Restaurant
        from tables.models import Order, OrderItem
        from datetime import date, timedelta
        from decimal import Decimal

        restaurant = Restaurant.objects.first()
        branch = restaurant.branches.first() if restaurant.branches.exists() else None
        today = date.today()

        print(f"Restaurant: {restaurant.name}")
        print(f"Today: {today}")

        # Get today's orders
        start_of_day = today.strftime('%Y-%m-%d 00:00:00')
        end_of_day = today.strftime('%Y-%m-%d 23:59:59')

        orders = Order.objects.filter(
            completed_at__range=[start_of_day, end_of_day],
            is_paid=True
        )

        print(f"Found {orders.count()} completed, paid orders")

        # Calculate totals
        total_revenue = Decimal('0.00')
        total_ingredient_cost = Decimal('0.00')
        order_count = orders.count()

        for order in orders:
            total_revenue += order.total_amount
            print(f"Order #{order.order_number}: ${order.total_amount:.2f}")

            for item in order.items.all():
                if item.menu_item and item.menu_item.cost_price:
                    item_cost = item.menu_item.cost_price * item.quantity
                    total_ingredient_cost += item_cost
                    print(
                        f"  - {item.menu_item.name}: {item.quantity} × ${item.unit_price:.2f} (cost: ${item.menu_item.cost_price:.2f})")

        # Calculate profit
        net_profit = total_revenue - total_ingredient_cost
        profit_margin = (net_profit / total_revenue *
                         100) if total_revenue > 0 else Decimal('0.00')
        avg_order_value = total_revenue / \
            order_count if order_count > 0 else Decimal('0.00')

        print(f"\n📊 FINAL CALCULATION:")
        print(f"  Revenue: ${total_revenue:.2f}")
        print(f"  Ingredient Cost: ${total_ingredient_cost:.2f}")
        print(f"  Net Profit: ${net_profit:.2f}")
        print(f"  Profit Margin: {profit_margin:.1f}%")
        print(f"  Orders: {order_count}")
        print(f"  Avg Order Value: ${avg_order_value:.2f}")

        # Save to ProfitAggregation
        from profit_intelligence.models import ProfitAggregation

        aggregation, created = ProfitAggregation.objects.update_or_create(
            date=today,
            restaurant=restaurant,
            branch=branch,
            defaults={
                'revenue': total_revenue,
                'cost_of_goods': total_ingredient_cost,
                'net_profit': net_profit,
                'profit_margin': profit_margin,
                'order_count': order_count,
                'average_order_value': avg_order_value,
                'waste_cost': Decimal('0.00'),
                'waste_percentage': Decimal('0.00'),
                'level': 'daily'
            }
        )

        if created:
            print(f"✅ Created new profit aggregation")
        else:
            print(f"✅ Updated existing profit aggregation")

        return True

    except Exception as e:
        print(f"❌ Error calculating profits: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboard_api():
    """Test the dashboard API directly"""
    print("\n🔍 TESTING DASHBOARD API...")

    try:
        import json
        from django.test import RequestFactory
        from profit_intelligence.api_views import ProfitDashboardAPIView
        from accounts.models import CustomUser

        # Get a manager/admin user
        user = CustomUser.objects.filter(role__in=['admin', 'manager']).first()
        if not user:
            user = CustomUser.objects.first()

        print(f"Testing with user: {user.username} (role: {user.role})")

        # Create a request with query parameters
        factory = RequestFactory()
        request = factory.get(
            '/profit-intelligence/api/dashboard/?view_level=branch')
        request.user = user

        # Call the API
        view = ProfitDashboardAPIView()
        view.request = request
        response = view.get(request)

        print("\nAPI Response:")
        print(json.dumps(response.data, indent=2))

        return True

    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("COMPREHENSIVE PROFIT DASHBOARD FIX")
    print("=" * 60)

    # Step 1: Fix database
    if not fix_database_tables():
        print("\n❌ Failed to fix database tables")
        return

    # Step 2: Fix API views
    if not fix_api_views():
        print("\n⚠️ Warning: Could not fix API views")

    # Step 3: Calculate profits
    if not calculate_profits():
        print("\n⚠️ Warning: Could not calculate profits")

    # Step 4: Test the API
    if not test_dashboard_api():
        print("\n⚠️ Warning: API test failed")

    print("\n" + "=" * 60)
    print("🎉 FIX COMPLETE!")
    print("=" * 60)
    print("\nNow visit the profit dashboard:")
    print("👉 http://localhost:8000/profit-intelligence/dashboard/")
    print("\nCheck the browser console (F12 → Console tab)")
    print("for any JavaScript errors.")


if __name__ == "__main__":
    main()
