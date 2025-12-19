from rest_framework import serializers
from .models import Table, Cart, CartItem, Order, OrderItem
from menu.serializers import MenuItemSerializer
from restaurants.serializers import BranchSerializer
from accounts.serializers import UserSerializer
from menu.models import MenuItem


class TableSerializer(serializers.ModelSerializer):
    branch_details = BranchSerializer(source='branch', read_only=True)
    qr_url = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    is_qr_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Table
        fields = [
            'id', 'branch', 'branch_details', 'table_number', 'table_name',
            'capacity', 'status', 'status_display', 'qr_code', 'qr_url',
            'qr_token', 'qr_expires_at', 'is_qr_valid', 'location_description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['qr_code', 'qr_token',
                            'qr_expires_at', 'created_at', 'updated_at']

    def get_qr_url(self, obj):
        if obj.qr_code:
            return obj.qr_code.url
        return None


class TableCreateSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(
        write_only=True, required=False, default=1)

    class Meta:
        model = Table
        fields = ['branch', 'table_number', 'table_name', 'capacity',
                  'status', 'location_description', 'is_active', 'count']

    def create(self, validated_data):
        count = validated_data.pop('count', 1)
        tables = []

        for i in range(count):
            table_data = validated_data.copy()
            if count > 1:
                table_data['table_number'] = f"{validated_data['table_number']}{i+1:02d}"

            table = Table.objects.create(**table_data)
            tables.append(table)

        if count == 1:
            return tables[0]
        return tables


class CartItemSerializer(serializers.ModelSerializer):
    menu_item_details = MenuItemSerializer(source='menu_item', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'menu_item', 'menu_item_details', 'quantity',
                  'special_instructions', 'total_price', 'created_at']
        read_only_fields = ['id', 'cart', 'created_at']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    table_details = TableSerializer(source='table', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'session_id', 'user', 'table', 'table_details',
                  'items', 'total_price', 'item_count', 'is_active',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'session_id', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_details = MenuItemSerializer(source='menu_item', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'menu_item', 'menu_item_details', 'quantity',
                  'unit_price', 'special_instructions', 'total_price']
        read_only_fields = ['id', 'order', 'unit_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table_details = TableSerializer(source='table', read_only=True)
    waiter_details = UserSerializer(source='waiter', read_only=True)
    order_type_display = serializers.CharField(
        source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    preparation_time = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'table', 'table_details', 'waiter', 'waiter_details',
            'customer_name', 'order_type', 'order_type_display', 'status', 'status_display',
            'notes', 'subtotal', 'tax_amount', 'service_charge', 'discount_amount',
            'total_amount', 'placed_at', 'confirmed_at', 'preparation_started_at',
            'ready_at', 'served_at', 'completed_at', 'cancelled_at', 'is_paid',
            'is_priority', 'requires_waiter_confirmation', 'items', 'preparation_time'
        ]
        read_only_fields = [
            'id', 'order_number', 'placed_at', 'confirmed_at', 'preparation_started_at',
            'ready_at', 'served_at', 'completed_at', 'cancelled_at'
        ]

    def get_preparation_time(self, obj):
        return obj.get_preparation_time()


class OrderCreateSerializer(serializers.ModelSerializer):
    cart_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = ['table', 'customer_name', 'order_type', 'notes',
                  'is_priority', 'cart_id']

    def create(self, validated_data):
        cart_id = validated_data.pop('cart_id', None)
        order = Order.objects.create(**validated_data)

        # If cart_id provided, transfer items from cart to order
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id)
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        menu_item=cart_item.menu_item,
                        quantity=cart_item.quantity,
                        special_instructions=cart_item.special_instructions
                    )

                # Deactivate cart
                cart.is_active = False
                cart.save()

                # Calculate totals
                order.calculate_totals()

            except Cart.DoesNotExist:
                pass

        return order


class QRValidationSerializer(serializers.Serializer):
    qr_token = serializers.CharField(max_length=100, required=True)
    table_id = serializers.IntegerField(required=False)


class CartAddItemSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    special_instructions = serializers.CharField(
        required=False, allow_blank=True)


class CartUpdateItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        required=True, min_value=0)  # 0 to remove


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Order.STATUS_CHOICES, required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


# In tables/serializers.py

class OrderWithItemsSerializer(serializers.Serializer):
    """Professional serializer for creating orders with items"""
    table = serializers.IntegerField(required=True)
    order_type = serializers.ChoiceField(
        choices=Order.ORDER_TYPE_CHOICES,
        required=True,
        error_messages={
            'invalid_choice': f"Must be one of: {[c[0] for c in Order.ORDER_TYPE_CHOICES]}"
        }
    )
    customer_name = serializers.CharField(
        required=False,
        default='Guest',
        max_length=100,
        trim_whitespace=True
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default=''
    )
    is_priority = serializers.BooleanField(default=False)

    items = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1,
        error_messages={
            'min_length': 'At least one item is required'
        }
    )

    def validate_table(self, value):
        """Validate table exists and is active"""
        try:
            table = Table.objects.get(id=value, is_active=True)
            return table.id
        except Table.DoesNotExist:
            raise serializers.ValidationError("Table not found or inactive")

    def validate_items(self, value):
        """Validate each item"""
        validated_items = []

        for idx, item in enumerate(value):
            # Check required fields
            if 'menu_item' not in item:
                raise serializers.ValidationError(
                    f"Item {idx}: 'menu_item' is required")
            if 'quantity' not in item:
                raise serializers.ValidationError(
                    f"Item {idx}: 'quantity' is required")

            # Validate types
            try:
                menu_item_id = int(item['menu_item'])
                quantity = int(item['quantity'])

                if quantity < 1:
                    raise serializers.ValidationError(
                        f"Item {idx}: Quantity must be positive")

                # Check menu item exists and is available
                menu_item = MenuItem.objects.get(id=menu_item_id)
                if not menu_item.is_available:
                    raise serializers.ValidationError(
                        f"Item {idx}: Menu item is not available")

                validated_items.append({
                    'menu_item': menu_item_id,
                    'quantity': quantity,
                    'special_instructions': str(item.get('special_instructions', '')).strip()
                })

            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"Item {idx}: Invalid data types")
            except MenuItem.DoesNotExist:
                raise serializers.ValidationError(
                    f"Item {idx}: Menu item not found")

        return validated_items
