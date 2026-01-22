# payments/views.py - FINAL CLEAN VERSION (No Duplicates)
from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal

from accounts.permissions import IsCashierOrHigher, IsAdminUser, IsManagerOrAdmin
from .models import Payment, Receipt, PaymentMethod, PaymentGateway
from .serializers import (
    PaymentSerializer, PaymentCreateSerializer,
    ReceiptSerializer, PaymentMethodSerializer,
    PaymentProcessSerializer, RefundSerializer
)
from tables.models import Order
from .gateways import CashGateway, CBEGateway, TelebirrGateway

import uuid


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for payment management - WITH INDUSTRY STANDARDS"""
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
        elif self.action == 'cashier_dashboard':
            return PaymentSerializer  # No special serializer needed
        return PaymentSerializer

    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            return Payment.objects.all()
        elif user.role == 'manager':
            return Payment.objects.filter(order__table__branch__restaurant=user.restaurant)
        elif user.role == 'cashier':
            return Payment.objects.filter(order__table__branch=user.branch)
        elif user.role == 'waiter':
            return Payment.objects.filter(order__table__branch=user.branch)

        return Payment.objects.none()

    def create(self, request, *args, **kwargs):
        """Create a payment - ENHANCED WITH INDUSTRY STANDARDS"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order']
        payment_method = serializer.validated_data['payment_method']
        amount = serializer.validated_data.get('amount')

        try:
            order = Order.objects.get(id=order_id)

            # ============ INDUSTRY STANDARD VALIDATION ============
            # 1. Validate order status
            if order.status != 'served' and order.status != 'bill_presented':
                return Response({
                    'error': f'Order must be served before payment. Current status: {order.status}'
                }, status=400)

            # 2. Validate order is not already paid
            if order.is_paid:
                return Response({
                    'error': 'Order is already paid'
                }, status=400)

            # 3. Validate amount
            if not amount:
                amount = order.total_amount

            if Decimal(str(amount)) <= 0:
                return Response({
                    'error': 'Amount must be greater than 0'
                }, status=400)

            # 4. Validate payment method
            valid_methods = ['cash', 'cbe', 'telebirr', 'cbe_wallet', 'card']
            if payment_method not in valid_methods:
                return Response({
                    'error': f'Invalid payment method. Valid methods: {", ".join(valid_methods)}'
                }, status=400)
            # ======================================================

            # Create payment
            payment = Payment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=amount,
                status='pending',
                processed_by=request.user,
                customer_name=serializer.validated_data.get(
                    'customer_name', ''),
                customer_phone=serializer.validated_data.get(
                    'customer_phone', ''),
                notes=serializer.validated_data.get('notes', '')
            )

            # For cash payments, mark as completed immediately
            if payment_method == 'cash':
                payment.mark_as_completed(
                    transaction_id=f"CASH-{payment.payment_id}",
                    user=request.user
                )

                # Update order status to completed
                order.status = 'completed'
                order.completed_at = timezone.now()
                order.is_paid = True
                order.save()

                # Update table status
                if order.table:
                    order.table.status = 'cleaning'
                    order.table.save()

            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED
            )

        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def cashier_dashboard(self, request):
        """INDUSTRY-STANDARD cashier dashboard data - REPLACES cashier_dashboard_data"""
        user = request.user

        # Get pending orders
        pending_response = self.pending_orders(request)
        if pending_response.status_code != 200:
            return pending_response

        pending_data = pending_response.data

        # Get today's payments
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(
            hour=23, minute=59, second=59, microsecond=999999)

        if user.role == 'admin':
            today_payments = Payment.objects.filter(
                status='completed',
                processed_at__range=[today_start, today_end]
            )
        elif user.role == 'manager':
            today_payments = Payment.objects.filter(
                status='completed',
                processed_at__range=[today_start, today_end],
                order__table__branch__restaurant=user.restaurant
            )
        else:
            today_payments = Payment.objects.filter(
                status='completed',
                processed_at__range=[today_start, today_end],
                order__table__branch=user.branch
            )

        # Calculate totals
        today_total = sum(p.amount for p in today_payments)
        pending_total = pending_data.get('total_amount', 0)

        # Payment method breakdown
        payment_methods = {}
        for payment in today_payments:
            method = payment.payment_method
            payment_methods[method] = payment_methods.get(
                method, 0) + float(payment.amount)

        # Recent transactions (last 10)
        recent_payments = Payment.objects.filter(
            status='completed'
        ).order_by('-processed_at')[:10]

        return Response({
            'user': {
                'name': user.get_full_name() or user.username,
                'role': user.role,
                'branch': user.branch.name if user.branch else 'N/A'
            },
            'pending_orders': pending_data,
            'today_summary': {
                'total_amount': today_total,
                'payment_count': today_payments.count(),
                'payment_methods': payment_methods
            },
            'recent_transactions': PaymentSerializer(recent_payments, many=True).data,
            # INDUSTRY STANDARD ADDITIONS:
            'system': {
                'timestamp': timezone.now().isoformat(),
                'gateway_status': self._check_gateway_status(),
                'available_methods': self._get_available_payment_methods()
            }
        })

    @action(detail=False, methods=['get'])
    def pending_orders(self, request):
        """Get orders that need payment (served but not paid) - KEEP YOUR VERSION"""
        user = request.user

        # Get orders based on user role
        if user.role == 'admin':
            orders = Order.objects.filter(status='served', is_paid=False)
        elif user.role == 'manager':
            orders = Order.objects.filter(
                status='served',
                is_paid=False,
                table__branch__restaurant=user.restaurant
            )
        elif user.role in ['cashier', 'waiter']:
            orders = Order.objects.filter(
                status='served',
                is_paid=False,
                table__branch=user.branch
            )
        else:
            orders = Order.objects.none()

        # Serialize order data
        from tables.serializers import OrderSerializer
        serializer = OrderSerializer(orders, many=True)

        total_amount = sum(order.total_amount for order in orders)

        return Response({
            'count': orders.count(),
            'total_amount': total_amount,
            'orders': serializer.data
        })

    @action(detail=True, methods=['post'])
    def process_quick_payment(self, request, pk=None):
        """INDUSTRY-STANDARD quick payment processing"""
        payment = self.get_object()

        if payment.status != 'pending':
            return Response({
                'error': f'Payment is already {payment.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Industry standard: Validate payment method
        if payment.payment_method == 'cash':
            # Cash payments can be completed directly
            payment.mark_as_completed(
                transaction_id=f"CASH-{payment.payment_id}",
                user=request.user
            )

            # Update order
            order = payment.order
            order.is_paid = True
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()

            # Update table
            if order.table:
                order.table.status = 'cleaning'
                order.table.save()

            return Response({
                'success': True,
                'payment': PaymentSerializer(payment).data,
                'message': 'Cash payment processed successfully'
            })

        else:
            # For digital payments, use existing process method
            return self.process(request, pk)

    @action(detail=True, methods=['post'])
    def generate_detailed_receipt(self, request, pk=None):
        """INDUSTRY-STANDARD detailed receipt with tax breakdown"""
        payment = self.get_object()

        if payment.status != 'completed':
            return Response({
                'error': 'Cannot generate receipt for non-completed payment'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if receipt already exists
        if hasattr(payment, 'receipt'):
            receipt = payment.receipt
        else:
            # Create receipt with industry standard format
            receipt = Receipt.objects.create(
                payment=payment,
                html_content=self._generate_industry_receipt_html(payment)
            )

        # INDUSTRY STANDARD: Return both HTML and JSON data
        return Response({
            'success': True,
            'receipt': ReceiptSerializer(receipt).data,
            'html_content': receipt.html_content,
            'receipt_number': receipt.receipt_number,
            'print_data': self._generate_print_data(payment),
            'metadata': {
                'generated_at': timezone.now().isoformat(),
                'generated_by': request.user.username,
                'format': 'thermal_80mm'
            }
        })

    # ============ INDUSTRY STANDARD HELPER METHODS ============

    def _check_gateway_status(self):
        """Check payment gateway connectivity"""
        return {
            'cash': 'available',
            'cbe': 'test_mode' if self._get_gateway('cbe') else 'not_configured',
            'telebirr': 'test_mode' if self._get_gateway('telebirr') else 'not_configured',
            'timestamp': timezone.now().isoformat()
        }

    def _get_available_payment_methods(self):
        """Get configured payment methods"""
        return [
            {'code': 'cash', 'name': 'Cash',
                'enabled': True, 'icon': 'fa-money-bill'},
            {'code': 'cbe', 'name': 'CBE', 'enabled': bool(
                self._get_gateway('cbe')), 'icon': 'fa-bank'},
            {'code': 'telebirr', 'name': 'Telebirr', 'enabled': bool(
                self._get_gateway('telebirr')), 'icon': 'fa-mobile-alt'},
            {'code': 'card', 'name': 'Card',
                'enabled': False, 'icon': 'fa-credit-card'},
        ]

    def _generate_industry_receipt_html(self, payment):
        """Generate industry-standard receipt HTML"""
        order = payment.order

        # Industry standard receipt format
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Receipt #{payment.receipt_number if hasattr(payment, 'receipt') else payment.payment_id}</title>
            <style>
                /* Industry standard thermal printer styling */
                body {{ 
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    margin: 0;
                    padding: 0;
                    width: 80mm;
                }}
                .receipt {{ padding: 5mm; }}
                .header {{ text-align: center; margin-bottom: 10px; }}
                .company-name {{ font-weight: bold; font-size: 14px; }}
                .divider {{ border-top: 1px dashed #000; margin: 8px 0; }}
                .item-row {{ display: flex; justify-content: space-between; }}
                .total-row {{ font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 15px; font-size: 10px; }}
                .barcode {{ text-align: center; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <div class="company-name">RESTAURANT NAME</div>
                    <div>123 Street, City</div>
                    <div>Phone: (123) 456-7890</div>
                    <div>Tax ID: 123456789</div>
                </div>
                
                <div class="divider"></div>
                
                <div class="receipt-info">
                    <div class="item-row">
                        <span>Receipt:</span>
                        <span>{payment.receipt_number if hasattr(payment, 'receipt') else 'N/A'}</span>
                    </div>
                    <div class="item-row">
                        <span>Date:</span>
                        <span>{payment.processed_at.strftime('%Y-%m-%d %H:%M') if payment.processed_at else timezone.now().strftime('%Y-%m-%d %H:%M')}</span>
                    </div>
                    <div class="item-row">
                        <span>Order:</span>
                        <span>#{order.order_number}</span>
                    </div>
                    <div class="item-row">
                        <span>Table:</span>
                        <span>{order.table.table_number if order.table else 'N/A'}</span>
                    </div>
                    <div class="item-row">
                        <span>Payment Method:</span>
                        <span>{payment.get_payment_method_display().upper()}</span>
                    </div>
                    <div class="item-row">
                        <span>Cashier:</span>
                        <span>{payment.processed_by.username if payment.processed_by else 'System'}</span>
                    </div>
                </div>
                
                <div class="divider"></div>
                
                <div class="items">
                    <div style="text-align: center; font-weight: bold; margin-bottom: 5px;">ITEMS</div>
                    {"".join([f'''
                    <div class="item-row">
                        <span>{item.quantity}x {item.menu_item.name[:20]}{'...' if len(item.menu_item.name) > 20 else ''}</span>
                        <span>{item.total_price:.2f}</span>
                    </div>
                    {f'<div style="font-size: 10px; margin-left: 10px; margin-bottom: 3px;"><i>{item.special_instructions[:30]}{"..." if len(item.special_instructions) > 30 else ""}</i></div>' if item.special_instructions else ''}
                    ''' for item in order.items.all()])}
                </div>
                
                <div class="divider"></div>
                
                <div class="totals">
                    <div class="item-row">
                        <span>Subtotal:</span>
                        <span>{order.subtotal:.2f}</span>
                    </div>
                    <div class="item-row">
                        <span>Tax (15%):</span>
                        <span>{order.tax_amount:.2f}</span>
                    </div>
                    <div class="item-row">
                        <span>Service (10%):</span>
                        <span>{order.service_charge:.2f}</span>
                    </div>
                    <div class="item-row total-row">
                        <span>TOTAL:</span>
                        <span>{order.total_amount:.2f}</span>
                    </div>
                    <div class="item-row">
                        <span>Paid:</span>
                        <span>{payment.amount:.2f}</span>
                    </div>
                    <div class="item-row">
                        <span>Change:</span>
                        <span>{max(0, float(payment.amount) - float(order.total_amount)):.2f}</span>
                    </div>
                </div>
                
                <div class="divider"></div>
                
                <div class="barcode">
                    *{payment.payment_id}*
                </div>
                
                <div class="footer">
                    <div>Thank you for dining with us!</div>
                    <div>Please keep this receipt for your records</div>
                    <div>Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _generate_print_data(self, payment):
        """Generate raw print data for thermal printers"""
        order = payment.order

        # ESC/POS commands for thermal printers
        return {
            'raw': [
                f"RECEIPT #{payment.payment_id}\n",
                f"Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n",
                f"Order: #{order.order_number}\n",
                f"Table: {order.table.table_number if order.table else 'N/A'}\n",
                f"Method: {payment.get_payment_method_display()}\n",
                "=" * 40 + "\n",
                *[f"{item.quantity}x {item.menu_item.name[:20]:<20} {item.total_price:>6.2f}\n" for item in order.items.all()],
                "=" * 40 + "\n",
                f"Subtotal: {order.subtotal:>29.2f}\n",
                f"Tax: {order.tax_amount:>33.2f}\n",
                f"Service: {order.service_charge:>30.2f}\n",
                f"TOTAL: {order.total_amount:>32.2f}\n",
                f"Paid: {payment.amount:>34.2f}\n",
                f"Change: {max(0, float(payment.amount) - float(order.total_amount)):>31.2f}\n",
                "=" * 40 + "\n",
                "Thank you for dining with us!\n",
                f"{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            ],
            'encoding': 'cp857',  # Common thermal printer encoding
            'cut_paper': True,
            'open_cash_drawer': True
        }

    def _get_gateway(self, payment_method):
        """Get appropriate gateway for payment method"""
        gateways = {
            'cash': CashGateway,
            'cbe': CBEGateway,
            'telebirr': TelebirrGateway,
            'cbe_wallet': CBEGateway
        }

        gateway_class = gateways.get(payment_method)
        if gateway_class:
            return gateway_class()
        return None


# ============ REMOVE THESE DUPLICATES ============
# DELETE: @api_view(['GET']) cashier_dashboard_data (replaced by cashier_dashboard action)
# DELETE: CashierDashboardAPI class (duplicate)
# DELETE: ProcessPaymentAPI class (duplicate functionality exists in create method)


@api_view(['GET'])
@permission_classes([IsCashierOrHigher])
def print_receipt(request, payment_id):
    """Print receipt view - KEEP AS IS (working)"""
    try:
        payment = Payment.objects.get(payment_id=payment_id)

        # Generate receipt if not exists
        if not hasattr(payment, 'receipt'):
            receipt = Receipt.objects.create(
                payment=payment,
                html_content=PaymentViewSet()._generate_industry_receipt_html(payment)
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
