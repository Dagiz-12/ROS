# payments/serializers.py
from rest_framework import serializers
from .models import Payment, Receipt, PaymentMethod, PaymentGateway
from tables.models import Order


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'code', 'is_active', 'requires_gateway']


class PaymentSerializer(serializers.ModelSerializer):
    order_details = serializers.SerializerMethodField()
    receipt_details = serializers.SerializerMethodField()
    processed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'order', 'order_details',
            'payment_method', 'amount', 'status',
            'transaction_id', 'processed_by', 'processed_by_name',
            'customer_name', 'customer_phone', 'notes',
            'created_at', 'processed_at', 'refunded_at',
            'receipt_details', 'table_number',
            'order_number',
        ]
        read_only_fields = ['payment_id', 'created_at',
                            'processed_at', 'refunded_at']

    def get_order_details(self, obj):
        if obj.order:
            return {
                'order_number': obj.order.order_number,
                'table_number': obj.order.table.table_number if obj.order.table else 'N/A',
                'total_amount': obj.order.total_amount,
                'status': obj.order.status
            }
        return None

    def get_receipt_details(self, obj):
        if hasattr(obj, 'receipt'):
            return {
                'receipt_number': obj.receipt.receipt_number,
                'printed': obj.receipt.printed_at is not None,
                'printed_at': obj.receipt.printed_at
            }
        return None

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return obj.processed_by.get_full_name() or obj.processed_by.username
        return None

    table_number = serializers.SerializerMethodField()

    def get_table_number(self, obj):
        return obj.order.table.table_number if obj.order and obj.order.table else None

    order_number = serializers.SerializerMethodField()

    def get_order_number(self, obj):
        return obj.order.order_number if obj.order else None


# In PaymentCreateSerializer, change the order field:
class PaymentCreateSerializer(serializers.Serializer):
    # CHANGED from PrimaryKeyRelatedField
    order = serializers.IntegerField(required=True)
    # OR use this if you want better validation:
    # order = serializers.PrimaryKeyRelatedField(
    #     queryset=Order.objects.all(),
    #     required=True
    # )

    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.PAYMENT_METHODS,
        required=True
    )
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, min_value=0.01
    )
    customer_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True)
    customer_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        # Get order ID from data
        order_id = data['order']

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise serializers.ValidationError('Order not found')

        # Replace order_id with order object for validation
        data['order_obj'] = order  # Add order object to validated data

        # Check if order is served
        if order.status != 'served':
            raise serializers.ValidationError(
                f'Order must be served before payment. Current status: {order.status}'
            )

        # Check if order is already paid
        if order.is_paid:
            raise serializers.ValidationError('Order is already paid')

        # Validate amount
        amount = data.get('amount')
        if amount and amount > order.total_amount:
            raise serializers.ValidationError(
                f'Payment amount ({amount}) cannot exceed order total ({order.total_amount})'
            )

        return data


class PaymentProcessSerializer(serializers.Serializer):
    customer_email = serializers.EmailField(required=False)
    customer_phone = serializers.CharField(max_length=20, required=False)
    save_payment_method = serializers.BooleanField(default=False)


class RefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, min_value=0.01
    )
    reason = serializers.CharField(required=False, allow_blank=True)


class ReceiptSerializer(serializers.ModelSerializer):
    payment_details = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_number', 'payment', 'payment_details',
            'printed_at', 'printed_by', 'email_sent', 'email_sent_at',
            'created_at'
        ]
        read_only_fields = ['receipt_number', 'created_at']

    def get_payment_details(self, obj):
        return {
            'payment_id': obj.payment.payment_id,
            'amount': obj.payment.amount,
            'payment_method': obj.payment.payment_method,
            'processed_at': obj.payment.processed_at
        }


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = [
            'id', 'gateway_type', 'name', 'is_active',
            'merchant_id', 'callback_url', 'test_mode',
            'created_at'
        ]
        read_only_fields = ['created_at']

# payments/serializers.py - ADD THIS


class CashierPaymentSerializer(serializers.ModelSerializer):
    """Simplified serializer for cashier dashboard"""
    order_number = serializers.CharField(
        source='order.order_number', read_only=True)
    table_number = serializers.CharField(
        source='order.table.table_number', read_only=True)
    customer_name = serializers.CharField(
        source='order.customer_name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'payment_id',
            'order_number',
            'table_number',
            'customer_name',
            'payment_method',
            'amount',
            'status',
            'processed_at',
            'created_at',
        ]
