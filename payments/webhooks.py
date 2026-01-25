# payments/webhooks.py - Industry standard webhook handling
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import hmac
import hashlib
import json


@csrf_exempt
@require_POST
def cbe_webhook(request):
    """CBE payment webhook - INDUSTRY STANDARD"""
    # 1. Verify signature
    signature = request.headers.get('X-CBE-Signature')
    payload = request.body

    if not verify_cbe_signature(payload, signature):
        return HttpResponseForbidden('Invalid signature')

    # 2. Parse and validate payload
    data = json.loads(payload)
    payment_id = data.get('payment_id')
    status = data.get('status')

    # 3. Update payment status
    payment = Payment.objects.get(payment_id=payment_id)
    payment.gateway_response = data
    payment.transaction_id = data.get('transaction_id')

    if status == 'SUCCESS':
        payment.mark_as_completed()
        # Update order
        payment.order.mark_paid('cbe', payment_id)
        # Update table
        if payment.order.table:
            payment.order.table.status = 'cleaning'
            payment.order.table.save()

    elif status == 'FAILED':
        payment.status = 'failed'
        payment.save()

    return JsonResponse({'success': True})
