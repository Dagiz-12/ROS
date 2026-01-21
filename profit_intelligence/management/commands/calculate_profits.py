# profit_intelligence/management/commands/calculate_profits.py
from django.core.management.base import BaseCommand
from profit_intelligence.business_logic import ProfitCalculator
from restaurants.models import Restaurant
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Calculate profits for the last 30 days'

    def handle(self, *args, **options):
        restaurants = Restaurant.objects.all()

        for restaurant in restaurants:
            self.stdout.write(f"Calculating profits for {restaurant.name}...")

            # Calculate for last 30 days
            for day_offset in range(30):
                target_date = date.today() - timedelta(days=day_offset)
                result = ProfitCalculator.calculate_daily_profit(
                    target_date, restaurant)

                if result['success']:
                    self.stdout.write(
                        f"  ✓ {target_date}: ${result['revenue']:.2f} revenue")
                else:
                    self.stdout.write(
                        f"  ✗ {target_date}: {result.get('error', 'Unknown error')}")

        self.stdout.write(self.style.SUCCESS('Profit calculations complete!'))
