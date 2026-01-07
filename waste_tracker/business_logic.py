# waste_tracker/business_logic.py
from django.db.models import Sum, Count, Avg, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import WasteRecord, WasteCategory, WasteReason, WasteTarget, WasteAlert
from inventory.models import StockTransaction, StockItem
from menu.models import MenuItem
from tables.models import Order


class EnhancedWasteAnalyzer:
    """
    Enhanced waste analysis with detailed tracking and insights
    """

    @staticmethod
    def analyze_detailed_waste_period(days=30, branch_id=None):
        """
        Comprehensive waste analysis with detailed breakdowns
        """
        start_date = timezone.now() - timedelta(days=days)

        # Base queryset
        queryset = WasteRecord.objects.filter(
            status='approved',
            created_at__gte=start_date
        )

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        # Summary statistics
        total_waste_cost = Decimal('0.00')
        total_waste_quantity = Decimal('0.00')
        waste_count = queryset.count()

        for record in queryset:
            if record.stock_transaction:
                total_waste_cost += record.stock_transaction.total_cost
                total_waste_quantity += record.stock_transaction.quantity

        # Waste by category
        waste_by_category = []
        categories = WasteCategory.objects.filter(is_active=True)

        for category in categories:
            category_waste = queryset.filter(waste_reason__category=category)
            category_cost = Decimal('0.00')
            category_count = category_waste.count()

            for record in category_waste:
                if record.stock_transaction:
                    category_cost += record.stock_transaction.total_cost

            if category_count > 0:
                waste_by_category.append({
                    'category_id': category.id,
                    'category_name': category.name,
                    'category_type': category.category_type,
                    'waste_count': category_count,
                    'total_cost': float(category_cost),
                    'percentage_of_total': float((category_cost / total_waste_cost * 100) if total_waste_cost > 0 else 0)
                })

        # Waste by reason
        waste_by_reason = []
        reasons = WasteReason.objects.filter(is_active=True)

        for reason in reasons:
            reason_waste = queryset.filter(waste_reason=reason)
            reason_cost = Decimal('0.00')
            reason_count = reason_waste.count()

            for record in reason_waste:
                if record.stock_transaction:
                    reason_cost += record.stock_transaction.total_cost

            if reason_count > 0:
                waste_by_reason.append({
                    'reason_id': reason.id,
                    'reason_name': reason.name,
                    'category_name': reason.category.name,
                    'controllability': reason.controllability,
                    'waste_count': reason_count,
                    'total_cost': float(reason_cost),
                    'avg_cost_per_incident': float(reason_cost / reason_count) if reason_count > 0 else 0
                })

        # Waste by kitchen station
        waste_by_station = []
        stations = queryset.exclude(station='').values('station').distinct()

        for station in stations:
            station_waste = queryset.filter(station=station['station'])
            station_cost = Decimal('0.00')
            station_count = station_waste.count()

            for record in station_waste:
                if record.stock_transaction:
                    station_cost += record.stock_transaction.total_cost

            waste_by_station.append({
                'station': station['station'],
                'waste_count': station_count,
                'total_cost': float(station_cost),
                'percentage_of_total': float((station_cost / total_waste_cost * 100) if total_waste_cost > 0 else 0)
            })

        # Waste by staff member
        waste_by_staff = []
        staff_records = queryset.values(
            'recorded_by__id', 'recorded_by__username').distinct()

        for staff in staff_records:
            staff_waste = queryset.filter(
                recorded_by__id=staff['recorded_by__id'])
            staff_cost = Decimal('0.00')
            staff_count = staff_waste.count()

            for record in staff_waste:
                if record.stock_transaction:
                    staff_cost += record.stock_transaction.total_cost

            waste_by_staff.append({
                'staff_id': staff['recorded_by__id'],
                'staff_username': staff['recorded_by__username'],
                'waste_count': staff_count,
                'total_cost': float(staff_cost),
                'avg_cost_per_incident': float(staff_cost / staff_count) if staff_count > 0 else 0
            })

        # Daily waste trend
        daily_trend = []
        for i in range(days):
            date = (timezone.now() - timedelta(days=i)).date()
            day_waste = queryset.filter(created_at__date=date)
            day_cost = Decimal('0.00')

            for record in day_waste:
                if record.stock_transaction:
                    day_cost += record.stock_transaction.total_cost

            daily_trend.append({
                'date': date.isoformat(),
                'day_name': date.strftime('%a'),
                'total': float(day_cost),
                'count': day_waste.count()
            })

        daily_trend.reverse()  # Oldest to newest

        # Top wasted items
        top_items = []
        item_records = {}

        for record in queryset:
            if record.stock_transaction and record.stock_transaction.stock_item:
                item_id = record.stock_transaction.stock_item.id
                if item_id not in item_records:
                    item_records[item_id] = {
                        'item': record.stock_transaction.stock_item,
                        'total_cost': Decimal('0.00'),
                        'total_quantity': Decimal('0.00'),
                        'count': 0
                    }

                item_records[item_id]['total_cost'] += record.stock_transaction.total_cost
                item_records[item_id]['total_quantity'] += record.stock_transaction.quantity
                item_records[item_id]['count'] += 1

        for item_data in sorted(item_records.values(), key=lambda x: x['total_cost'], reverse=True)[:10]:
            top_items.append({
                'item_id': item_data['item'].id,
                'item_name': item_data['item'].name,
                'category': item_data['item'].category,
                'unit': item_data['item'].unit,
                'total_cost': float(item_data['total_cost']),
                'total_quantity': float(item_data['total_quantity']),
                'waste_count': item_data['count'],
                'avg_cost_per_incident': float(item_data['total_cost'] / item_data['count']) if item_data['count'] > 0 else 0
            })

        # Calculate waste percentage of food cost
        # This would need integration with your sales/order data
        # For now, we'll use a placeholder
        # Placeholder - you would calculate this from orders
        food_cost_period = Decimal('0.00')
        waste_percentage = (total_waste_cost / (food_cost_period +
                            total_waste_cost) * 100) if food_cost_period > 0 else 0

        return {
            'period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': timezone.now().date()
            },
            'summary': {
                'total_waste_cost': float(total_waste_cost),
                'total_waste_quantity': float(total_waste_quantity),
                'waste_count': waste_count,
                'waste_percentage': float(waste_percentage),
                'avg_daily_waste': float(total_waste_cost / days),
                'avg_cost_per_incident': float(total_waste_cost / waste_count) if waste_count > 0 else 0
            },
            'by_category': waste_by_category,
            'by_reason': waste_by_reason,
            'by_station': waste_by_station,
            'by_staff': waste_by_staff,
            'daily_trend': daily_trend,
            'top_items': top_items,
            'industry_benchmark': {
                'average_waste_percentage': 5.0,  # Industry average
                'good_waste_percentage': 3.0,     # Good target
                'excellent_waste_percentage': 1.5  # Excellent target
            }
        }

    @staticmethod
    def detect_recurring_issues(days=30):
        """
        Detect patterns of recurring waste issues
        """
        start_date = timezone.now() - timedelta(days=days)

        # Get all waste records
        waste_records = WasteRecord.objects.filter(
            status='approved',
            created_at__gte=start_date
        )

        recurring_issues = []

        # Group by stock item and waste reason
        from collections import defaultdict
        issue_patterns = defaultdict(list)

        for record in waste_records:
            if record.stock_transaction:
                key = (record.stock_transaction.stock_item.id,
                       record.waste_reason.id)
                issue_patterns[key].append(record)

        # Analyze patterns
        for (item_id, reason_id), records in issue_patterns.items():
            if len(records) >= 3:  # At least 3 occurrences to be considered recurring
                # Calculate statistics
                total_cost = sum(
                    r.stock_transaction.total_cost for r in records if r.stock_transaction)
                avg_days_between = 0

                if len(records) > 1:
                    dates = sorted([r.created_at for r in records])
                    total_days = (dates[-1] - dates[0]).days
                    avg_days_between = total_days / (len(records) - 1)

                # Get involved staff
                staff_involved = set(r.recorded_by.username for r in records)
                stations_involved = set(
                    r.station for r in records if r.station)

                # Check if already has recurrence_id
                recurrence_ids = set(
                    r.recurrence_id for r in records if r.recurrence_id)

                recurring_issues.append({
                    'item_id': item_id,
                    'item_name': records[0].stock_transaction.stock_item.name if records[0].stock_transaction else 'Unknown',
                    'reason_id': reason_id,
                    'reason_name': records[0].waste_reason.name,
                    'occurrence_count': len(records),
                    'total_cost': float(total_cost),
                    'avg_cost_per_incident': float(total_cost / len(records)),
                    'avg_days_between': avg_days_between,
                    'staff_involved': list(staff_involved),
                    'stations_involved': list(stations_involved),
                    'recurrence_ids': list(recurrence_ids),
                    'first_occurrence': min(r.created_at for r in records),
                    'last_occurrence': max(r.created_at for r in records)
                })

        # Sort by total cost (most expensive issues first)
        recurring_issues.sort(key=lambda x: x['total_cost'], reverse=True)

        return {
            'period_days': days,
            'total_recurring_issues': len(recurring_issues),
            # 50% reduction potential
            'estimated_savings': sum(issue['total_cost'] * 0.5 for issue in recurring_issues),
            'issues': recurring_issues
        }

    @staticmethod
    def calculate_waste_reduction_potential(branch_id=None):
        """
        Calculate potential waste reduction and savings
        """
        # Get controllable waste (waste with controllable reasons)
        controllable_reasons = WasteReason.objects.filter(
            controllability__in=['controllable', 'partially_controllable'],
            is_active=True
        )

        start_date = timezone.now() - timedelta(days=90)  # Last 90 days
        queryset = WasteRecord.objects.filter(
            waste_reason__in=controllable_reasons,
            status='approved',
            created_at__gte=start_date
        )

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        # Calculate current waste
        total_controllable_waste = Decimal('0.00')
        for record in queryset:
            if record.stock_transaction:
                total_controllable_waste += record.stock_transaction.total_cost

        # Reduction potential assumptions
        reduction_potentials = {
            'spoilage': 0.6,  # 60% reduction possible
            'preparation': 0.4,  # 40% reduction possible
            'overproduction': 0.7,  # 70% reduction possible
            'portion_control': 0.5,  # 50% reduction possible
            'other': 0.3  # 30% reduction possible
        }

        # Calculate by category
        reduction_by_category = []
        for category in WasteCategory.objects.filter(is_active=True):
            category_waste = queryset.filter(waste_reason__category=category)
            category_cost = Decimal('0.00')

            for record in category_waste:
                if record.stock_transaction:
                    category_cost += record.stock_transaction.total_cost

            reduction_potential = reduction_potentials.get(
                category.category_type, 0.3)
            potential_savings = category_cost * \
                Decimal(str(reduction_potential))

            if category_cost > 0:
                reduction_by_category.append({
                    'category_name': category.name,
                    'category_type': category.category_type,
                    'current_waste': float(category_cost),
                    'reduction_potential': reduction_potential * 100,  # As percentage
                    'potential_savings': float(potential_savings),
                    # Divide by 3 months
                    'savings_per_month': float(potential_savings / 3)
                })

        # Total potential savings
        total_potential_savings = sum(
            item['potential_savings'] for item in reduction_by_category)
        monthly_potential_savings = sum(
            item['savings_per_month'] for item in reduction_by_category)

        return {
            'analysis_period_days': 90,
            'total_controllable_waste': float(total_controllable_waste),
            'reduction_by_category': reduction_by_category,
            'total_potential_savings': float(total_potential_savings),
            'monthly_potential_savings': float(monthly_potential_savings),
            'recommended_actions': [
                "Implement portion control training",
                "Review and adjust preparation quantities",
                "Improve inventory rotation (FIFO)",
                "Monitor expiration dates closely",
                "Train staff on proper storage"
            ]
        }

    @staticmethod
    def generate_waste_forecast(days=30, branch_id=None):
        """
        Generate waste forecast based on historical patterns
        """
        # Get historical data (last 90 days for better prediction)
        start_date = timezone.now() - timedelta(days=90)
        queryset = WasteRecord.objects.filter(
            status='approved',
            created_at__gte=start_date
        )

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        # Group by day of week and calculate averages
        day_of_week_patterns = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday

        for record in queryset:
            if record.stock_transaction:
                day_of_week = record.created_at.weekday()
                day_of_week_patterns[day_of_week].append(
                    float(record.stock_transaction.total_cost)
                )

        # Calculate average waste by day of week
        avg_by_day = {}
        for day, costs in day_of_week_patterns.items():
            if costs:
                avg_by_day[day] = sum(costs) / len(costs)
            else:
                avg_by_day[day] = 0

        # Generate forecast
        forecast = []
        day_names = ['Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday', 'Sunday']

        for i in range(days):
            forecast_date = timezone.now() + timedelta(days=i)
            day_of_week = forecast_date.weekday()

            # Base forecast on historical average
            base_forecast = avg_by_day.get(day_of_week, 0)

            # Adjust for weekends (typically higher waste)
            adjustment = 1.2 if day_of_week >= 5 else 1.0  # 20% higher on weekends

            forecast.append({
                'date': forecast_date.date().isoformat(),
                'day_name': day_names[day_of_week],
                'forecasted_waste': base_forecast * adjustment,
                'confidence': 'medium' if len(day_of_week_patterns[day_of_week]) >= 5 else 'low'
            })

        # Calculate total forecast
        total_forecast = sum(day['forecasted_waste'] for day in forecast)

        return {
            'forecast_period_days': days,
            'total_forecasted_waste': total_forecast,
            'daily_forecast': forecast,
            'historical_basis_days': 90,
            'notes': 'Forecast based on historical day-of-week patterns. Higher waste expected on weekends.'
        }


class WasteAlertManager:
    """
    Manage waste-related alerts and notifications
    """

    @staticmethod
    def check_daily_thresholds(branch_id=None):
        """
        Check if daily waste thresholds are exceeded
        """
        today = timezone.now().date()
        today_start = timezone.make_aware(
            datetime.combine(today, datetime.min.time()))

        # Get today's waste
        queryset = WasteRecord.objects.filter(
            status='approved',
            created_at__gte=today_start
        )

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        # Calculate total waste today
        total_today = Decimal('0.00')
        for record in queryset:
            if record.stock_transaction:
                total_today += record.stock_transaction.total_cost

        # Check against threshold (e.g., $100 daily threshold)
        daily_threshold = Decimal('100.00')

        if total_today > daily_threshold:
            # Create alert
            from .models import WasteAlert
            WasteAlert.objects.create(
                alert_type='threshold_exceeded',
                title='Daily Waste Threshold Exceeded',
                message=f'Daily waste cost (${total_today:.2f}) has exceeded threshold (${daily_threshold:.2f})',
                branch_id=branch_id
            )

            return {
                'threshold_exceeded': True,
                'current_waste': float(total_today),
                'threshold': float(daily_threshold),
                'excess': float(total_today - daily_threshold)
            }

        return {'threshold_exceeded': False, 'current_waste': float(total_today)}

    @staticmethod
    def check_recurring_issues():
        """
        Check for and alert on recurring waste issues
        """
        recurring_issues = EnhancedWasteAnalyzer.detect_recurring_issues(
            days=7)  # Check last 7 days

        alerts_created = []

        for issue in recurring_issues['issues']:
            if issue['occurrence_count'] >= 3:  # Alert if 3+ occurrences in 7 days
                from .models import WasteAlert

                # Find a representative record
                record = WasteRecord.objects.filter(
                    stock_transaction__stock_item_id=issue['item_id'],
                    waste_reason_id=issue['reason_id']
                ).first()

                alert = WasteAlert.objects.create(
                    alert_type='recurring_issue',
                    title=f'Recurring Waste: {issue["item_name"]}',
                    message=f'{issue["item_name"]} has been wasted {issue["occurrence_count"]} times '
                    f'in the last 7 days due to {issue["reason_name"]}. Total cost: ${issue["total_cost"]:.2f}',
                    waste_record=record,
                    waste_reason_id=issue['reason_id'],
                    branch_id=record.branch_id if record else None
                )

                alerts_created.append({
                    'alert_id': alert.id,
                    'item_name': issue['item_name'],
                    'reason_name': issue['reason_name'],
                    'occurrence_count': issue['occurrence_count'],
                    'total_cost': issue['total_cost']
                })

        return {
            'alerts_created': len(alerts_created),
            'details': alerts_created
        }

    @staticmethod
    def check_pending_approvals():
        """
        Check for waste records pending approval
        """
        pending_records = WasteRecord.objects.filter(status='pending')

        if pending_records.exists():
            from .models import WasteAlert

            # Group by branch
            branches = {}
            for record in pending_records:
                branch_id = record.branch_id
                if branch_id not in branches:
                    branches[branch_id] = {
                        'count': 0,
                        'total_cost': Decimal('0.00'),
                        'branch_name': record.branch.name
                    }

                branches[branch_id]['count'] += 1
                if record.stock_transaction:
                    branches[branch_id]['total_cost'] += record.stock_transaction.total_cost

            # Create alerts for each branch with pending approvals
            alerts_created = []
            for branch_id, data in branches.items():
                if data['count'] > 0:
                    alert = WasteAlert.objects.create(
                        alert_type='approval_needed',
                        title=f'{data["count"]} Waste Records Pending Approval',
                        message=f'{data["count"]} waste records totaling ${data["total_cost"]:.2f} need approval',
                        branch_id=branch_id
                    )
                    alerts_created.append(alert.id)

            return {
                'pending_records': pending_records.count(),
                'branches_affected': len(branches),
                'alerts_created': len(alerts_created)
            }

        return {'pending_records': 0, 'alerts_created': 0}
