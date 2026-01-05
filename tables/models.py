from decimal import Decimal
from django.db import models
from django.conf import settings
from restaurants.models import Branch
import qrcode
import io
from django.core.files.base import ContentFile
import uuid
from django.utils import timezone
from menu.models import MenuItem


class Table(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('cleaning', 'Cleaning'),
        ('out_of_service', 'Out of Service'),
    ]

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=20)
    table_name = models.CharField(
        max_length=100, blank=True, null=True)  # Optional friendly name
    capacity = models.IntegerField(default=4)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='available')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_token = models.CharField(
        max_length=100, unique=True, blank=True, null=True)
    qr_expires_at = models.DateTimeField(blank=True, null=True)
    # e.g., "Near window", "Private corner"
    location_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['table_number']
        unique_together = ['branch', 'table_number']

    def __str__(self):
        branch_name = self.branch.name if self.branch else "No Branch"
        return f"Table {self.table_number} - {branch_name}"

    def save(self, *args, **kwargs):
        # Generate QR token if not exists
        if not self.qr_token:
            self.qr_token = f"{self.branch.id}:{uuid.uuid4().hex}"
            self.qr_expires_at = timezone.now() + timezone.timedelta(hours=4)  # 4-hour expiry

        # Generate QR code image if not exists
        if not self.qr_code and self.qr_token:
            self.generate_qr_code()

        super().save(*args, **kwargs)

    def generate_qr_code(self):
        """Generate QR code for the table"""
        # Create QR code data
        qr_data = f"http://localhost:8000/qr-menu/{self.branch.restaurant.id}/{self.id}/"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to BytesIO
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Save to ImageField
        filename = f"table_{self.table_number}_{self.branch.id}_qr.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)

    def is_qr_valid(self):
        """Check if QR token is still valid"""
        if not self.qr_expires_at:
            return False
        return timezone.now() < self.qr_expires_at

    def refresh_qr_token(self):
        """Refresh QR token (for security)"""
        self.qr_token = f"{self.branch.id}:{uuid.uuid4().hex}"
        self.qr_expires_at = timezone.now() + timezone.timedelta(hours=4)
        self.generate_qr_code()
        self.save()


# Additional models related to table reservations, orders, etc.


class Cart(models.Model):
    """Shopping cart for customers (before order submission)"""
    session_id = models.CharField(
        max_length=100, blank=True, null=True)  # For guest users
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts'
    )  # For registered users
    table = models.ForeignKey(
        Table, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username} at Table {self.table.table_number}"
        return f"Cart (Session: {self.session_id}) at Table {self.table.table_number}"

    @property
    def total_price(self):
        """Calculate total price of all items in cart"""
        return sum(item.total_price for item in self.items.all())

    @property
    def item_count(self):
        """Count total items in cart"""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """Individual items in the cart"""
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['cart', 'menu_item', 'special_instructions']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    @property
    def total_price(self):
        """Calculate price for this cart item"""
        return self.menu_item.price * self.quantity


class Order(models.Model):
    """Main order model (after cart submission)"""
    ORDER_TYPE_CHOICES = [
        ('qr', 'QR Order'),
        ('waiter', 'Waiter Assisted'),
        ('online', 'Online Order'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Waiter Confirmation'),
        ('confirmed', 'Confirmed by Waiter'),
        ('preparing', 'Preparing in Kitchen'),
        ('ready', 'Ready for Serving'),
        ('served', 'Served to Customer'),
        ('completed', 'Completed (Meal Finished)'),
        ('cancelled', 'Cancelled'),
    ]

    # Order identification
    order_number = models.CharField(
        max_length=20, unique=True, blank=True, null=True)
    table = models.ForeignKey(
        Table, on_delete=models.CASCADE, related_name='orders')
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='waiter_orders'
    )
    customer_name = models.CharField(
        max_length=100, blank=True)  # For walk-in customers

    # Order details
    order_type = models.CharField(
        max_length=20, choices=ORDER_TYPE_CHOICES, default='qr')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)  # General order notes

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    # Timestamps
    placed_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    preparation_started_at = models.DateTimeField(blank=True, null=True)
    ready_at = models.DateTimeField(blank=True, null=True)
    served_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    # Flags
    is_paid = models.BooleanField(default=False)
    is_priority = models.BooleanField(default=False)  # Rush order flag
    requires_waiter_confirmation = models.BooleanField(
        default=True)  # For QR orders

    class Meta:
        ordering = ['-placed_at']
        indexes = [
            models.Index(fields=['status', 'placed_at']),
            models.Index(fields=['table', 'placed_at']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Order #{self.order_number} - Table {self.table.table_number}"

    def save(self, *args, **kwargs):
        # Generate order number if not exists
        if not self.order_number:
            self.order_number = self.generate_order_number()

        # Calculate totals if not set
        if not self.total_amount and self.pk:
            self.calculate_totals()

        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number"""
        from datetime import datetime
        date_str = datetime.now().strftime('%y%m%d')

        # Get last order number for today
        last_order = Order.objects.filter(
            order_number__startswith=date_str
        ).order_by('-order_number').first()

        if last_order:
            last_num = int(last_order.order_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{date_str}{new_num:04d}"

    # In tables/models.py - Order model

    def calculate_totals(self):
        """Calculate order totals from items"""
        from decimal import Decimal

        items = self.items.all()

        # Calculate subtotal
        self.subtotal = Decimal('0.00')
        for item in items:
            self.subtotal += item.total_price

        # Use Decimal for tax and service calculations
        tax_rate = Decimal('0.15')  # 15%
        service_rate = Decimal('0.10')  # 10%

        self.tax_amount = self.subtotal * tax_rate
        self.service_charge = self.subtotal * service_rate

        # Calculate total
        self.total_amount = (self.subtotal +
                             self.tax_amount +
                             self.service_charge -
                             self.discount_amount)

        # Round to 2 decimal places
        self.subtotal = self.subtotal.quantize(Decimal('0.01'))
        self.tax_amount = self.tax_amount.quantize(Decimal('0.01'))
        self.service_charge = self.service_charge.quantize(Decimal('0.01'))
        self.total_amount = self.total_amount.quantize(Decimal('0.01'))

        # Save only these fields
        update_fields = ['subtotal', 'tax_amount',
                         'service_charge', 'total_amount']
        self.save(update_fields=update_fields)

    def get_preparation_time(self):
        """Estimate preparation time based on items"""
        if not self.preparation_started_at:
            return None

        if self.ready_at:
            return (self.ready_at - self.preparation_started_at).total_seconds() / 60

        # Return estimated time based on menu items
        items = self.items.all()
        if items:
            max_time = max(item.menu_item.preparation_time for item in items)
            return max_time

        return 30  # Default 30 minutes

    def mark_confirmed(self, waiter):
        """Mark order as confirmed by waiter"""
        self.status = 'confirmed'
        self.waiter = waiter
        self.confirmed_at = timezone.now()
        self.requires_waiter_confirmation = False
        self.save()

    def mark_preparing(self):
        """Mark order as being prepared"""
        self.status = 'preparing'
        self.preparation_started_at = timezone.now()
        self.save()

    def mark_ready(self):
        """Mark order as ready for serving"""
        self.status = 'ready'
        self.ready_at = timezone.now()
        self.save()

    def mark_served(self):
        """Mark order as served to customer"""
        self.status = 'served'
        self.served_at = timezone.now()
        self.save()

    def mark_completed(self, update_sales=True):
        """Mark order as completed and update sales statistics"""
        self.status = 'completed'
        self.completed_at = timezone.now()

        if update_sales:
            # Update menu item sales statistics
            for order_item in self.items.all():
                menu_item = order_item.menu_item
                menu_item.update_sales(order_item.quantity)

        self.save()


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2)  # Price at time of order
    special_instructions = models.TextField(blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} (Order #{self.order.order_number})"

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def save(self, *args, **kwargs):
        # Store current menu item price
        if not self.unit_price:
            self.unit_price = self.menu_item.price
        super().save(*args, **kwargs)


#
