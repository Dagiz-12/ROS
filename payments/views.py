# payments/views.py - COMPLETE FIXED VERSION
from rest_framework.views import APIView
from django.conf import settings
from accounts.permissions import IsCashierOrHigher, IsAdminUser, IsManagerOrAdmin
from rest_framework.decorators import api_view, permission_classes
import logging
from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from django.utils import timezone
from decimal import Decimal
import uuid
import json
from datetime import timedelta

from .models import Payment, Receipt, PaymentMethod, PaymentGateway
from .serializers import (
    PaymentSerializer, PaymentCreateSerializer,
    ReceiptSerializer, PaymentMethodSerializer,
    PaymentProcessSerializer, RefundSerializer, CashierPaymentSerializer
)
from tables.models import Order
from .gateways import CashGateway, CBEGateway, TelebirrGateway

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for payment management"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsCashierOrHigher]

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action == 'process':
            return PaymentProcessSerializer
        elif self.action == 'refund':
            return RefundSerializer
        return PaymentSerializer

    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            return Payment.objects.all()
        elif user.role == 'manager':
            return Payment.objects.filter(order__branch__restaurant=user.restaurant)
        elif user.role in ['cashier', 'waiter']:
            return Payment.objects.filter(order__branch=user.branch)
        return Payment.objects.none()

    def create(self, request, *args, **kwargs):
        """Create a payment"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data.get('order')
        payment_method = serializer.validated_data['payment_method']
        amount = serializer.validated_data.get('amount')

        # Get order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

        # Validate order can be paid
        if order.is_paid:
            return Response({'error': 'Order already paid'}, status=400)

        # Create payment
        payment = Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=amount or order.total_amount,
            status='pending',
            processed_by=request.user,
            customer_name=serializer.validated_data.get('customer_name', ''),
            customer_phone=serializer.validated_data.get('customer_phone', ''),
            notes=serializer.validated_data.get('notes', '')
        )

        # For cash payments, mark as completed immediately
        if payment_method == 'cash':
            payment.mark_as_completed(
                transaction_id=f"CASH-{payment.payment_id}",
                user=request.user
            )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process a payment"""
        payment = self.get_object()

        if payment.status != 'pending':
            return Response({
                'error': f'Payment is already {payment.status}'
            }, status=400)

        # Process based on payment method
        if payment.payment_method == 'cash':
            payment.mark_as_completed(
                transaction_id=f"CASH-{payment.payment_id}",
                user=request.user
            )
        else:
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.transaction_id = f"{payment.payment_method.upper()}-{payment.payment_id}"
            payment.save()

        return Response({
            'success': True,
            'payment': PaymentSerializer(payment).data,
            'message': f'{payment.payment_method.upper()} payment processed successfully'
        })


# ============ CASHIER ENDPOINTS ============

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCashierOrHigher])
def cashier_dashboard_data(request):
    """
    Get dashboard data for cashier interface.
    This is the MAIN endpoint that your JavaScript calls.
    """
    try:
        user = request.user
        logger.info(f"Cashier {user.username} requesting dashboard data")

        # Check if user has a branch assigned
        if not user.branch:
            return Response({
                'success': False,
                'error': 'Cashier not assigned to a branch'
            }, status=400)

        # ============ FIXED: Get orders that need payment ============
        # Look for ANY orders that are not paid (not just 'served' status)
        pending_orders = Order.objects.filter(
            table__branch=user.branch,  # FIXED: Changed from 'branch' to 'table__branch'
            is_paid=False  # ANY unpaid order
        ).select_related('table', 'table__branch').order_by('-placed_at')

        logger.info(
            f"Found {pending_orders.count()} unpaid orders in branch {user.branch.name}")

        # ============ Get today's completed payments ============
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        today_payments = Payment.objects.filter(
            order__table__branch=user.branch,  # FIXED
            status='completed',
            processed_at__range=[today_start, today_end]
        )

        # ============ Calculate today's revenue ============
        today_revenue = sum(p.amount for p in today_payments)

        # ============ Get recent payments (last 10) ============
        recent_payments = Payment.objects.filter(
            order__table__branch=user.branch,  # FIXED: Changed from 'order__branch'
            status='completed'
        ).select_related('order', 'order__table').order_by('-processed_at')[:20]

        # ============ Serialize data ============
        # Fix: Get all pending orders data
        pending_orders_data = []
        for order in pending_orders:
            pending_orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'table_number': order.table.table_number if order.table else 'N/A',
                'customer_name': order.customer_name or 'Guest',
                'total_amount': float(order.total_amount),
                'status': order.status,
                'is_paid': order.is_paid,
                'placed_at': order.placed_at,
                'waiter_name': order.waiter.get_full_name() if order.waiter else 'N/A',
                'items_count': order.items.count()  # FIXED: Use 'items' not 'orderitem_set'
            })

        # Fix: Get recent payments data
        recent_payments_data = []
        for payment in recent_payments:
            recent_payments_data.append({
                'id': str(payment.payment_id),
                'order_number': payment.order.order_number if payment.order else 'N/A',
                'table_number': payment.order.table.table_number if payment.order and payment.order.table else 'N/A',
                'payment_method': payment.get_payment_method_display(),
                'amount': float(payment.amount),
                'status': payment.status,
                'processed_at': payment.processed_at,
                'customer_name': payment.customer_name or 'Guest'
            })

        return Response({
            'success': True,
            'data': {
                'pending_orders': {
                    'count': len(pending_orders_data),
                    'orders': pending_orders_data
                },
                'today_summary': {
                    'revenue': float(today_revenue),
                    'transactions': today_payments.count(),
                    'average_transaction': float(today_revenue / today_payments.count()) if today_payments.count() > 0 else 0
                },
                'recent_payments': recent_payments_data,
                'branch': {
                    'id': user.branch.id,
                    'name': user.branch.name
                },
                'cashier': {
                    'id': user.id,
                    'name': user.get_full_name() or user.username,
                    'role': user.role
                }
            }
        })

    except Exception as e:
        logger.error(f"Cashier dashboard error: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Failed to load dashboard data',
            'details': str(e) if settings.DEBUG else None
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCashierOrHigher])
def cashier_process_payment(request):
    """
    Process payment from cashier dashboard.
    This endpoint should create a Payment record and update the Order.
    """
    try:
        data = request.data
        order_id = data.get('order_id')
        payment_method = data.get('payment_method', 'cash')
        amount = data.get('amount')
        cash_received = data.get('cash_received')
        customer_name = data.get('customer_name', 'Guest')
        customer_phone = data.get('customer_phone', '')

        # Validate required fields
        if not order_id or not amount:
            return Response({
                'success': False,
                'error': 'Missing required fields: order_id and amount'
            }, status=400)

        # Get order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=404)

        # Check if order is already paid
        if order.is_paid:
            return Response({
                'success': False,
                'error': 'Order is already paid'
            }, status=400)

        # Validate amount
        amount_decimal = Decimal(str(amount))
        if amount_decimal <= Decimal('0.00'):
            return Response({
                'success': False,
                'error': 'Amount must be greater than 0'
            }, status=400)

        # ============ CREATE PAYMENT ============
        payment = Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=amount_decimal,
            status='pending',
            processed_by=request.user,
            customer_name=customer_name,
            customer_phone=customer_phone,
            notes=f'Processed via cashier dashboard by {request.user.username}'
        )

        # ============ PROCESS BASED ON PAYMENT METHOD ============
        if payment_method == 'cash':
            # Calculate change
            change = Decimal('0.00')
            if cash_received:
                cash_received_decimal = Decimal(str(cash_received))
                change = cash_received_decimal - amount_decimal

            payment.metadata = {
                'cash_received': str(cash_received) if cash_received else str(amount),
                'change': str(change),
                'processed_via': 'cashier_dashboard'
            }

            # Mark as completed immediately
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.transaction_id = f"CASH-{payment.payment_id}"
            payment.save()

            # Update order
            order.is_paid = True
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()

            # Update table status
            if order.table:
                order.table.status = 'cleaning'
                order.table.save()

            # Generate receipt
            receipt = Receipt.objects.create(
                payment=payment,
                html_content=generate_receipt_html(payment, float(change))
            )

            response_data = {
                'success': True,
                'payment': PaymentSerializer(payment).data,
                'receipt': {
                    'receipt_number': receipt.receipt_number,
                    'html_content': receipt.html_content,
                    'printable': True
                },
                'change': float(change) if change > Decimal('0.00') else 0,
                'message': 'Cash payment processed successfully'
            }

        else:
            # Digital payment - mark as pending
            response_data = {
                'success': True,
                'payment': PaymentSerializer(payment).data,
                'message': f'{payment_method.upper()} payment initiated. Awaiting confirmation.'
            }

        # Log the payment
        logger.info(
            f'Payment {payment.payment_id} processed: ${amount_decimal} via {payment_method} for Order {order.order_number}')

        return Response(response_data, status=201)

    except Exception as e:
        logger.error(f'Payment processing error: {str(e)}', exc_info=True)
        return Response({
            'success': False,
            'error': 'Internal server error',
            'details': str(e) if settings.DEBUG else None
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCashierOrHigher])
def cashier_pending_orders(request):
    """Get orders pending payment for cashier dashboard"""
    user = request.user

    # Get orders that need payment
    if user.role == 'admin':
        orders = Order.objects.filter(is_paid=False)
    elif user.role == 'manager':
        orders = Order.objects.filter(
            is_paid=False,
            table__branch__restaurant=user.restaurant  # FIXED: table__branch__restaurant
        )
    else:
        orders = Order.objects.filter(
            is_paid=False,
            table__branch=user.branch  # FIXED: table__branch
        )

    from tables.serializers import OrderSerializer
    serializer = OrderSerializer(orders, many=True)

    return Response({
        'orders': serializer.data,
        'count': orders.count(),
        'total_amount': sum(order.total_amount for order in orders)
    })


# ============ HELPER FUNCTIONS ============

def generate_receipt_html(payment, change=0):
    """Generate receipt HTML"""
    order = payment.order
    change_decimal = Decimal(str(change)) if change else Decimal('0.00')

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Receipt {payment.payment_id}</title>
        <style>
            body {{ font-family: 'Courier New', monospace; font-size: 12px; margin: 0; padding: 0; width: 80mm; }}
            .receipt {{ padding: 5mm; }}
            .header {{ text-align: center; margin-bottom: 10px; }}
            .company-name {{ font-weight: bold; font-size: 14px; }}
            .divider {{ border-top: 1px dashed #000; margin: 8px 0; }}
            .item-row {{ display: flex; justify-content: space-between; }}
            .total-row {{ font-weight: bold; }}
            .footer {{ text-align: center; margin-top: 15px; font-size: 10px; }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <div class="company-name">RESTAURANT ORDERING SYSTEM</div>
                <div>Payment Receipt</div>
            </div>
            
            <div class="divider"></div>
            
            <div class="receipt-info">
                <div class="item-row">
                    <span>Receipt:</span>
                    <span>{payment.payment_id}</span>
                </div>
                <div class="item-row">
                    <span>Date:</span>
                    <span>{payment.processed_at.strftime('%Y-%m-%d %H:%M:%S') if payment.processed_at else timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                </div>
                <div class="item-row">
                    <span>Order:</span>
                    <span>#{order.order_number}</span>
                </div>
                <div class="item-row">
                    <span>Table:</span>
                    <span>{order.table.table_number if order.table else 'N/A'}</span>
                </div>
            </div>
            
            <div class="divider"></div>
            
            <div class="payment-details">
                <div class="item-row">
                    <span>Payment Method:</span>
                    <span>{payment.get_payment_method_display()}</span>
                </div>
                <div class="item-row">
                    <span>Amount Paid:</span>
                    <span>${payment.amount}</span>
                </div>
                {f'<div class="item-row"><span>Change:</span><span>${change_decimal}</span></div>' if change_decimal > Decimal("0.00") else ''}
                <div class="item-row">
                    <span>Cashier:</span>
                    <span>{payment.processed_by.username if payment.processed_by else 'System'}</span>
                </div>
            </div>
            
            <div class="divider"></div>
            
            <div class="footer">
                <div>Thank you for your payment!</div>
                <div>Receipt ID: {payment.payment_id}</div>
                <div>Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
        </div>
    </body>
    </html>
    """


# ============ OTHER ENDPOINTS (KEEP FOR COMPATIBILITY) ============

@api_view(['GET'])
@permission_classes([IsCashierOrHigher])
def print_receipt(request, payment_id):
    """Print receipt view"""
    try:
        payment = Payment.objects.get(payment_id=payment_id)

        # Generate receipt if not exists
        if not hasattr(payment, 'receipt'):
            receipt = Receipt.objects.create(
                payment=payment,
                html_content=generate_receipt_html(payment)
            )
        else:
            receipt = payment.receipt

        # Mark as printed
        receipt.mark_printed(user=request.user)

        # Return HTML for printing
        from django.http import HttpResponse
        return HttpResponse(receipt.html_content)

    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCashierOrHigher])
def process_cash_payment(request):
    """Legacy: Process cash payment"""
    try:
        data = request.data
        order_id = data.get('order_id')
        amount = data.get('amount')

        if not order_id or not amount:
            return Response({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        order = Order.objects.get(id=order_id)

        # Create payment
        payment = Payment.objects.create(
            order=order,
            payment_method='cash',
            amount=amount,
            status='completed',
            processed_by=request.user
        )

        # Update order
        order.is_paid = True
        order.status = 'completed'
        order.completed_at = timezone.now()
        order.save()

        return Response({
            'success': True,
            'payment_id': str(payment.payment_id),
            'message': 'Cash payment processed'
        })

    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)
    except Exception as e:
        logger.error(f"Cash payment error: {str(e)}")
        return Response({'error': str(e)}, status=500)


# ============ VIEW CLASSES ============

class CashierPaymentAPI(APIView):
    """Cashier payment processing endpoint"""
    permission_classes = [IsAuthenticated, IsCashierOrHigher]

    def post(self, request):
        """Process payment from cashier dashboard"""
        return cashier_process_payment(request)
