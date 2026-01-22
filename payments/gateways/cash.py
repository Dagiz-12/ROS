# payments/gateways/cash.py
from .base import BasePaymentGateway


class CashGateway(BasePaymentGateway):
    """Cash payment gateway (no external API needed)"""

    def initiate_payment(self, payment_data):
        """For cash payments, we just mark as completed"""
        return {
            'success': True,
            'transaction_id': f"CASH-{payment_data.get('payment_id')}",
            'status': 'completed',
            'message': 'Cash payment received',
            'amount': payment_data.get('amount'),
            'payment_method': 'cash'
        }

    def verify_payment(self, transaction_id):
        """Cash payments don't need verification"""
        return {
            'success': True,
            'status': 'completed',
            'verified_at': self._get_current_time()
        }

    def refund_payment(self, transaction_id, amount):
        """Cash refund - handled manually"""
        return {
            'success': True,
            'message': 'Cash refund processed manually',
            'refund_id': f"REFUND-{transaction_id}",
            'amount': amount
        }

    def _get_current_time(self):
        from django.utils import timezone
        return timezone.now()
