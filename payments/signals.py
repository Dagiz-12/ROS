# payments/signals.py - FIXED VERSION
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from tables.models import Order
from .models import Payment
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def update_order_on_payment_completion(sender, instance, created, **kwargs):
    """
    Update order when payment is marked as completed
    This is the MAIN signal that syncs payment → order
    """
    if instance.status == 'completed' and instance.order:
        order = instance.order

        # Only update if order isn't already marked as paid
        if not order.is_paid:
            logger.info(
                f"💰 Payment {instance.payment_id} completed for Order {order.order_number}")

            # Mark order as paid and completed
            order.is_paid = True
            order.status = 'completed'
            order.completed_at = timezone.now()

            # Store payment info in metadata
            if not hasattr(order, 'metadata'):
                order.metadata = {}
            order.metadata['payment_method'] = instance.payment_method
            order.metadata['payment_id'] = str(instance.payment_id)
            order.metadata['paid_at'] = order.completed_at.isoformat()

            order.save()

            # Update table status to cleaning
            if order.table:
                order.table.status = 'cleaning'
                order.table.save()

            logger.info(
                f"Created payment {instance.payment_id} for Order {order.order_number}")


@receiver(post_save, sender=Order)
def auto_create_payment_on_served(sender, instance, created, **kwargs):
    """
    Automatically create pending payment when order is served
    This triggers when order status changes to 'served'
    """
    # Only run on update (not creation) and when status is 'served'
    if created:
        return

    try:
        # Get the original order to check status change
        if hasattr(instance, '_original_status'):
            original_status = instance._original_status
            current_status = instance.status

            # Only create payment when status changes TO 'served'
            if original_status != 'served' and current_status == 'served':
                logger.info(
                    f"🍽️ Order {instance.order_number} served, creating payment...")

                # Check if payment already exists
                existing_payment = Payment.objects.filter(
                    order=instance,
                    status__in=['pending', 'completed']
                ).first()

                if not existing_payment:
                    # Create pending payment
                    payment = Payment.objects.create(
                        order=instance,
                        payment_method='pending',  # Will be set by cashier
                        amount=instance.total_amount,
                        status='pending',
                        processed_by=instance.waiter if instance.waiter else None,
                        customer_name=instance.customer_name or 'Guest',
                        notes=f'Auto-created when order #{instance.order_number} served'
                    )
                    logger.info(
                        f"✅ Created payment {payment.payment_id} for Order {instance.order_number}")
                else:
                    logger.info(
                        f"⚠️ Payment already exists: {existing_payment.payment_id}")

    except Exception as e:
        logger.error(
            f"❌ Error creating payment for order {instance.id}: {str(e)}")

# Track original status before save


@receiver(pre_save, sender=Order)
def track_order_status(sender, instance, **kwargs):
    """
    Track original status to detect changes
    """
    if instance.pk:
        try:
            original = Order.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Order.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Order)
def cleanup_original_status(sender, instance, **kwargs):
    """
    Clean up the temporary attribute
    """
    if hasattr(instance, '_original_status'):
        delattr(instance, '_original_status')
