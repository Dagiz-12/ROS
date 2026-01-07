# waste_tracker/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import WasteRecord, WasteAlert


@receiver(post_save, sender=WasteRecord)
def handle_waste_record_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save actions for WasteRecord
    """
    if created:
        # New waste record created

        # Check if this looks like a recurring issue
        if not instance.is_recurring_issue:
            instance._detect_recurring_issue()
            instance.save(
                update_fields=['is_recurring_issue', 'recurrence_id'])

        # Check if approval is needed
        if instance.waste_reason.category.requires_approval:
            # Create approval needed alert
            WasteAlert.objects.create(
                alert_type='approval_needed',
                title=f'Waste Record Needs Approval',
                message=f'Waste record for {instance.stock_item.name if instance.stock_item else "Unknown Item"} '
                f'needs approval. Reason: {instance.waste_reason.name}',
                waste_record=instance,
                branch=instance.branch
            )

        # Check waste reason thresholds
        if instance.waste_reason.alert_threshold_daily > 0:
            # Check daily threshold for this reason
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_waste = WasteRecord.objects.filter(
                waste_reason=instance.waste_reason,
                status='approved',
                created_at__gte=today_start,
                branch=instance.branch
            )

            total_today_cost = 0
            for record in today_waste:
                if record.stock_transaction:
                    total_today_cost += record.stock_transaction.total_cost

            if total_today_cost >= instance.waste_reason.alert_threshold_daily:
                WasteAlert.objects.create(
                    alert_type='threshold_exceeded',
                    title=f'Daily Threshold Exceeded: {instance.waste_reason.name}',
                    message=f'Daily waste cost for {instance.waste_reason.name} has reached '
                    f'${total_today_cost:.2f} (threshold: ${instance.waste_reason.alert_threshold_daily:.2f})',
                    waste_reason=instance.waste_reason,
                    branch=instance.branch
                )

    else:
        # Waste record updated

        # If status changed to approved
        if instance.status == 'approved' and instance._old_status != 'approved':
            # Check if this completes a recurring issue pattern
            if instance.is_recurring_issue:
                # Count occurrences with same recurrence_id
                similar_issues = WasteRecord.objects.filter(
                    recurrence_id=instance.recurrence_id,
                    status='approved'
                ).count()

                if similar_issues >= 3:  # Alert after 3 approved occurrences
                    WasteAlert.objects.create(
                        alert_type='recurring_issue',
                        title=f'Recurring Waste Issue Confirmed',
                        message=f'{similar_issues} occurrences of {instance.waste_reason.name} '
                        f'for {instance.stock_item.name if instance.stock_item else "Unknown Item"}',
                        waste_record=instance,
                        waste_reason=instance.waste_reason,
                        branch=instance.branch
                    )


@receiver(pre_save, sender=WasteRecord)
def capture_old_status(sender, instance, **kwargs):
    """
    Capture the old status before save to detect changes
    """
    if instance.pk:
        try:
            old_instance = WasteRecord.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except WasteRecord.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=WasteAlert)
def handle_waste_alert_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save actions for WasteAlert
    """
    if created:
        # New alert created
        # Could send notifications here (email, push, etc.)
        pass

    if instance.is_resolved and not instance.resolved_at:
        # Alert was just resolved
        instance.resolved_at = timezone.now()
        instance.save(update_fields=['resolved_at'])
