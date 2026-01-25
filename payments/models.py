# payments/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class PaymentMethod(models.Model):
    """Available payment methods"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('cbe', 'Commercial Bank of Ethiopia (CBE)'),
        ('telebirr', 'Telebirr'),
        ('cbe_wallet', 'CBE Wallet'),
        ('card', 'Credit/Debit Card'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    requires_gateway = models.BooleanField(default=False)
    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Payment(models.Model):
    """Main payment model"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    # Order relationship
    order = models.ForeignKey(
        'tables.Order', on_delete=models.CASCADE, related_name='payments')

    # Payment details
    payment_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[
                                 MinValueValidator(Decimal('0.01'))])
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Transaction details (for digital payments)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)

    # User tracking
    processed_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL,
                                     null=True, related_name='processed_payments')
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)

    # Notes and metadata
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    refunded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['transaction_id']),
        ]

    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount} ETB"

    def save(self, *args, **kwargs):
        # Auto-set processed_at when status changes to completed
        if self.status == 'completed' and not self.processed_at:
            self.processed_at = timezone.now()

        # Auto-set refunded_at when status changes to refunded
        if self.status == 'refunded' and not self.refunded_at:
            self.refunded_at = timezone.now()

        super().save(*args, **kwargs)

    def mark_as_completed(self, transaction_id=None, gateway_response=None, user=None):
        """Mark payment as completed"""
        self.status = 'completed'
        self.processed_at = timezone.now()

        if transaction_id:
            self.transaction_id = transaction_id

        if gateway_response:
            self.gateway_response = gateway_response

        if user:
            self.processed_by = user

        self.save()

        # Update order payment status
        self.order.is_paid = True
        self.order.save()

        return self

    @property
    def is_digital_payment(self):
        """Check if payment is digital (not cash)"""
        return self.payment_method in ['cbe', 'telebirr', 'cbe_wallet', 'card']

    @classmethod
    def check_duplicate_payment(cls, order, payment_method, amount):
        """Check for duplicate payments (same order, method, amount within 5 minutes)"""
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)

        duplicate = cls.objects.filter(
            order=order,
            payment_method=payment_method,
            amount=amount,
            created_at__gte=five_minutes_ago,
            status__in=['completed', 'pending']
        ).exists()

        return duplicate


class Receipt(models.Model):
    """Receipt generation and tracking"""
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    html_content = models.TextField()  # HTML for printing
    printed_at = models.DateTimeField(blank=True, null=True)
    printed_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    # For digital receipts
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Receipt {self.receipt_number} for Payment {self.payment.payment_id}"

    def generate_receipt_number(self):
        """Generate unique receipt number"""
        from datetime import datetime
        date_str = datetime.now().strftime('%y%m%d')

        # Get last receipt number for today
        last_receipt = Receipt.objects.filter(
            receipt_number__startswith=f"R{date_str}"
        ).order_by('-receipt_number').first()

        if last_receipt:
            last_num = int(last_receipt.receipt_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"R{date_str}{new_num:04d}"

    def save(self, *args, **kwargs):
        # Generate receipt number if not exists
        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()

        super().save(*args, **kwargs)

    def mark_printed(self, user=None):
        """Mark receipt as printed"""
        self.printed_at = timezone.now()
        self.printed_by = user
        self.save()
        return self


class PaymentGateway(models.Model):
    """Payment gateway configuration"""
    GATEWAY_TYPES = [
        ('cbe', 'Commercial Bank of Ethiopia'),
        ('telebirr', 'Telebirr'),
        ('cbe_wallet', 'CBE Wallet'),
        ('test', 'Test Gateway'),
    ]

    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPES)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    # Configuration
    api_key = models.CharField(max_length=200, blank=True)
    api_secret = models.CharField(max_length=200, blank=True)
    merchant_id = models.CharField(max_length=100, blank=True)
    callback_url = models.URLField(blank=True)

    # Endpoints
    initiate_url = models.URLField(blank=True)
    verify_url = models.URLField(blank=True)
    refund_url = models.URLField(blank=True)

    # Settings
    test_mode = models.BooleanField(default=True)
    enabled_payment_methods = models.JSONField(default=list, blank=True)

    restaurant = models.ForeignKey(
        'restaurants.Restaurant', on_delete=models.CASCADE)

    class Meta:
        ordering = ['name']
        unique_together = ['gateway_type', 'restaurant']

    def __str__(self):
        return f"{self.name} ({'Test' if self.test_mode else 'Live'})"
