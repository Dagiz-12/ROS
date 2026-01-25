# payments/validators.py
from django.utils import timezone
from decimal import Decimal
from .models import Payment


class PaymentValidator:
    """INDUSTRY STANDARD payment validation"""

    @staticmethod
    def validate_payment_request(order, payment_method, amount, user):
        """Validate payment request before processing"""
        errors = []

        # 1. Order validation
        if not order:
            errors.append('Order not found')
            return False, errors

        # 2. Order status validation
        valid_statuses = ['served', 'bill_presented', 'payment_pending']
        if order.status not in valid_statuses:
            errors.append(
                f'Order status must be one of: {", ".join(valid_statuses)}. Current: {order.status}')

        # 3. Already paid validation
        if order.is_paid:
            errors.append('Order is already paid')

        # 4. Amount validation
        if amount <= Decimal('0.00'):
            errors.append('Amount must be greater than 0')

        # Allow 50% overpayment max
        if amount > order.total_amount * Decimal('1.5'):
            errors.append(
                f'Amount (${amount}) is too high. Order total: ${order.total_amount}')

        # 5. Payment method validation
        valid_methods = ['cash', 'cbe', 'telebirr', 'cbe_wallet']
        if payment_method not in valid_methods:
            errors.append(
                f'Invalid payment method. Must be one of: {", ".join(valid_methods)}')

        # 6. Duplicate payment check
        recent_payment = Payment.objects.filter(
            order=order,
            amount=amount,
            payment_method=payment_method,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).first()

        if recent_payment:
            errors.append(
                f'Duplicate payment detected. Payment ID: {recent_payment.payment_id}')

        return len(errors) == 0, errors

    @staticmethod
    def validate_cash_payment(cash_received, amount_due):
        """Validate cash payment amounts"""
        if cash_received < amount_due:
            return False, f'Cash received (${cash_received}) is less than amount due (${amount_due})'

        # Calculate change
        change = cash_received - amount_due

        # Warn about large change (industry standard: alert for change > $50)
        if change > Decimal('50.00'):
            return True, f'Large change due: ${change}. Please verify cash received.'

        return True, f'Change due: ${change}'
