# profit_intelligence/waste_integration.py
import logging
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def get_waste_costs_for_date(date, restaurant, branch=None):
    """
    Get waste costs for a specific date from waste tracker
    """
    try:
        # Import here to avoid circular imports
        from waste_tracker.models import WasteRecord

        logger.info(
            f"Getting waste costs for {date} - Restaurant: {restaurant.name}, Branch: {branch.name if branch else 'All'}")

        # Get waste records
        waste_records = WasteRecord.objects.filter(
            status='approved',
            recorded_at__date=date,
            branch__restaurant=restaurant
        )

        if branch:
            waste_records = waste_records.filter(branch=branch)

        logger.info(f"Found {waste_records.count()} waste records for {date}")

        total_waste_cost = Decimal('0.00')
        waste_details = []

        for record in waste_records:
            cost = Decimal('0.00')
            if record.stock_transaction:
                cost = record.stock_transaction.total_cost or Decimal('0.00')

            total_waste_cost += cost

            waste_details.append({
                'id': record.id,
                'item': record.stock_item.name if record.stock_item else 'Unknown Item',
                'quantity': float(record.quantity) if record.quantity else 0.0,
                'unit': record.stock_item.unit if record.stock_item else '',
                'reason': record.waste_reason.name if record.waste_reason else 'Unknown Reason',
                'cost': float(cost),
                'station': record.station or 'Unknown',
                'recorded_by': record.recorded_by.username if record.recorded_by else 'Unknown'
            })

        logger.info(f"Total waste cost for {date}: ${total_waste_cost:.2f}")

        return {
            'total_cost': float(total_waste_cost),
            'record_count': waste_records.count(),
            'details': waste_details
        }

    except Exception as e:
        logger.error(
            f"Error getting waste costs for {date}: {str(e)}", exc_info=True)
        return {
            'total_cost': 0.0,
            'record_count': 0,
            'details': []
        }
