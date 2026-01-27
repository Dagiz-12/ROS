# payments/signals.py - SIMPLIFIED VERSION
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from tables.models import Order
from .models import Payment
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])


logger = logging.getLogger(__name__)

# Store original status before saving
_original_status_cache = {}


@receiver(post_save, sender=Order)
def auto_create_payment_on_order_update(sender, instance, created, **kwargs):
    """
    Create payment record when order status changes to 'served' or 'bill_presented'
    """
    try:
        # Get original status from cache
        original_status = _original_status_cache.get(instance.pk)

        # Check if this is an update (not creation)
        if not created and original_status is not None:
            current_status = instance.status

            # Check if status changed TO 'served' or 'bill_presented'
            if (original_status != current_status and
                current_status in ['served', 'bill_presented'] and
                    not instance.is_paid):

                logger.info(
                    f"Order {instance.order_number} {current_status}, checking for payment...")

                # Check if payment already exists
                existing_payment = Payment.objects.filter(
                    order=instance,
                    status__in=['pending', 'completed']
                ).first()

                if not existing_payment:
                    # Create pending payment
                    payment = Payment.objects.create(
                        order=instance,
                        payment_method='pending',
                        amount=instance.total_amount,
                        status='pending',
                        branch=instance.branch,
                        customer_name=instance.customer_name or 'Guest',
                        notes=f'Auto-created when order status changed to {current_status}'
                    )

                    logger.info(
                        f"✅ Created payment {payment.payment_id} for Order {instance.order_number}")

        # Clear the cache
        if instance.pk in _original_status_cache:
            del _original_status_cache[instance.pk]

    except Exception as e:
        logger.error(f"Error in auto_create_payment_on_order_update: {str(e)}")

# Cache the original status before saving


@receiver(pre_save, sender=Order)
def cache_original_status(sender, instance, **kwargs):
    """
    Cache the original status before saving
    """
    if instance.pk:
        try:
            original = Order.objects.get(pk=instance.pk)
            _original_status_cache[instance.pk] = original.status
        except Order.DoesNotExist:
            pass


@receiver(post_save, sender=Payment)
def update_order_on_payment_completion(sender, instance, created, **kwargs):
    """
    Update order when payment is completed
    """
    if instance.status == 'completed' and instance.order:
        order = instance.order

        if not order.is_paid:
            order.is_paid = True
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()

            logger.info(
                f"💰 Payment {instance.payment_id} completed for Order {order.order_number}")

            # Update table
            if order.table:
                order.table.status = 'cleaning'
                order.table.save()
