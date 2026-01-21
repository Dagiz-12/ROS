# Add this at the top of waste_tracker/models.py or create a utils.py
from decimal import Decimal


def get_waste_record_cost(waste_record):
    """Safely get cost from waste record through stock_transaction"""
    if waste_record.stock_transaction:
        return waste_record.stock_transaction.total_cost
    return Decimal('0.00')


def get_waste_record_quantity(waste_record):
    """Safely get quantity from waste record through stock_transaction"""
    if waste_record.stock_transaction:
        return waste_record.stock_transaction.quantity
    return Decimal('0.00')


def get_waste_record_stock_item(waste_record):
    """Safely get stock item from waste record"""
    if waste_record.stock_transaction:
        return waste_record.stock_transaction.stock_item
    return None
