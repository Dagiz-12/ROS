# In waste_tracker/management/commands/setup_waste_data.py
from django.core.management.base import BaseCommand
from waste_tracker.models import WasteCategory, WasteReason
from restaurants.models import Restaurant


class Command(BaseCommand):
    help = 'Create sample waste categories and reasons'

    def handle(self, *args, **options):
        restaurant = Restaurant.objects.first()
        if not restaurant:
            self.stdout.write(self.style.ERROR('No restaurant found'))
            return

        # Create waste categories
        categories = [
            ('spoilage', 'Spoilage/Expired', '#ff6b6b'),
            ('preparation', 'Preparation Waste', '#4ecdc4'),
            ('overproduction', 'Overproduction', '#45b7d1'),
            ('customer_return', 'Customer Return', '#96ceb4'),
            ('portion_control', 'Portion Control Issue', '#feca57'),
        ]

        for cat_type, name, color in categories:
            category, created = WasteCategory.objects.get_or_create(
                name=name,
                restaurant=restaurant,
                defaults={
                    'category_type': cat_type,
                    'color_code': color,
                    'description': f'{name} waste category'
                }
            )

            if created:
                self.stdout.write(f'Created category: {name}')

                # Create reasons for this category
                reasons = [
                    ('Expired', 'Item past expiry date',
                     'uncontrollable', False, False),
                    ('Spoiled', 'Item spoiled before expiry',
                     'controllable', True, False),
                    ('Damaged packaging', 'Packaging damaged during handling',
                     'partially_controllable', False, False),
                ]

                for reason_name, desc, control, req_exp, req_photo in reasons:
                    WasteReason.objects.create(
                        name=reason_name,
                        description=desc,
                        category=category,
                        controllability=control,
                        requires_explanation=req_exp,
                        requires_photo=req_photo,
                        is_active=True
                    )
                    self.stdout.write(f'  - Created reason: {reason_name}')

        self.stdout.write(self.style.SUCCESS('Sample waste data created'))
