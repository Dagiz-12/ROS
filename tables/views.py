from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
import uuid
from django.http import HttpResponseForbidden
from django.conf import settings
from django.http import HttpResponse
from accounts.decorators import role_required, check_role


from .models import Table, Cart, CartItem, Order, OrderItem
from .serializers import (
    TableSerializer, TableCreateSerializer, CartSerializer, CartItemSerializer,
    OrderSerializer, OrderCreateSerializer, QRValidationSerializer,
    CartAddItemSerializer, CartUpdateItemSerializer, OrderStatusUpdateSerializer, OrderWithItemsSerializer, OrderItemSerializer
)
from menu.models import MenuItem
from accounts.permissions import IsAdminUser, IsManagerOrAdmin, IsWaiterOrHigher, IsCashierOrHigher, IsChefOrHigher


# ==================== HTML TEMPLATE VIEWS ====================

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render


# def check_role(user, allowed_roles):
#   """Check if user has one of the allowed roles"""
#  return hasattr(user, 'role') and user.role in allowed_roles


# def role_required(allowed_roles):
#   """Decorator to check user role"""
#  def decorator(view_func):
#     @login_required
#    def wrapper(request, *args, **kwargs):
#       if not check_role(request.user, allowed_roles):
#          from django.http import HttpResponseForbidden
#         return HttpResponseForbidden("Permission denied")
#    return view_func(request, *args, **kwargs)
# return wrapper
# return decorator

# QR Menu Template View - ALREADY EXISTS (keep it)


def qr_menu_view(request, restaurant_id=None, table_id=None):
    """Serve the QR menu interface"""
    context = {
        'restaurant_id': restaurant_id or 1,
        'table_id': table_id or 1,
    }
    return render(request, 'qr_menu/index.html', context)

# ==================== WAITER INTERFACE ====================


@role_required(['waiter', 'manager', 'admin'])
def waiter_dashboard(request):
    """Waiter Tablet Interface - Dashboard"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'waiter/dashboard.html', context)


@role_required(['waiter', 'manager', 'admin'])
def waiter_tables(request):
    """Waiter - Table management view"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'waiter/tables.html', context)


@role_required(['waiter', 'manager', 'admin'])
def waiter_orders(request):
    """Waiter - Order management view"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'waiter/orders.html', context)


@role_required(['waiter', 'manager', 'admin'])
def waiter_new_order(request, table_id=None):
    """Waiter - Create new order interface"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
        'table_id': table_id,
    }
    return render(request, 'waiter/new_order.html', context)

# ==================== CHEF INTERFACE ====================


@role_required(['chef', 'manager', 'admin'])
def chef_dashboard(request):
    """Chef Kitchen Display - Main dashboard"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'chef/dashboard.html', context)

# ==================== CASHIER INTERFACE ====================


@role_required(['cashier', 'manager', 'admin'])
def cashier_dashboard(request):
    """Cashier Payment Interface"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'cashier/dashboard.html', context)

# ==================== ADMIN DASHBOARD ====================


@role_required(['admin', 'manager'])
def admin_dashboard(request):
    """Admin Dashboard Interface"""
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'admin_dashboard/index.html', context)


class TableViewSet(viewsets.ModelViewSet):
    """ViewSet for table management"""
    queryset = Table.objects.all()
    # Allow waiters and higher to manage tables
    permission_classes = [IsWaiterOrHigher]
    # Remove DjangoFilterBackend due to compatibility issues with django-filter
    # and Django versions causing ChoiceField initialization errors.
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    # Keep filterset_fields for future use if DjangoFilterBackend is restored
    filterset_fields = ['branch', 'status', 'is_active']
    search_fields = ['table_number', 'table_name', 'location_description']
    ordering_fields = ['table_number', 'capacity', 'created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return TableCreateSerializer
        return TableSerializer

    def get_queryset(self):
        user = self.request.user

        # Admin can see all tables
        if user.role == 'admin':
            return Table.objects.all()

        # Manager can see tables from their restaurant
        elif user.role == 'manager':
            if user.restaurant:
                return Table.objects.filter(branch__restaurant=user.restaurant)

        # Other roles can see tables from their branch
        elif user.branch:
            return Table.objects.filter(branch=user.branch)

        return Table.objects.none()

    @action(detail=True, methods=['post'])
    def refresh_qr(self, request, pk=None):
        """Refresh QR code for table"""
        table = self.get_object()
        table.refresh_qr_token()
        serializer = self.get_serializer(table)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_branch(self, request):
        """Get tables grouped by branch"""
        branch_id = request.query_params.get('branch_id')
        if not branch_id:
            return Response({'error': 'branch_id required'}, status=400)

        tables = Table.objects.filter(branch_id=branch_id, is_active=True)
        serializer = self.get_serializer(tables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update table status"""
        table = self.get_object()
        user = request.user
        new_status = request.data.get('status')

        if new_status not in dict(Table.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=400)

        # Validate status transition based on user role
        if not self.validate_table_status_transition(table.status, new_status, user.role):
            return Response({
                'error': f'Cannot change status from {table.status} to {new_status}'
            }, status=400)

        table.status = new_status
        table.save()
        serializer = self.get_serializer(table)
        return Response(serializer.data)

    def validate_table_status_transition(self, current_status, new_status, user_role):
        """Validate if table status transition is allowed for user role"""
        valid_transitions = {
            'waiter': {
                'available': ['reserved'],  # Waiters can reserve tables
                # Waiters can unreserve OR mark as occupied
                'reserved': ['available', 'occupied'],
                # Waiters can mark occupied as cleaning
                'occupied': ['cleaning'],
                # Waiters can mark cleaning tables as available
                'cleaning': ['available'],
                'out_of_service': [],  # Waiters cannot modify out_of_service tables
            },
            'manager': {
                'available': ['reserved', 'out_of_service', 'occupied'],
                'occupied': ['cleaning', 'available', 'out_of_service'],
                'reserved': ['available', 'occupied', 'out_of_service'],
                'cleaning': ['available', 'out_of_service'],
                'out_of_service': ['available', 'reserved'],
            },
            'admin': {
                'available': ['reserved', 'out_of_service', 'occupied'],
                'occupied': ['cleaning', 'available', 'out_of_service'],
                'reserved': ['available', 'occupied', 'out_of_service'],
                'cleaning': ['available', 'out_of_service'],
                'out_of_service': ['available', 'reserved', 'occupied'],
            },
        }

        if user_role not in valid_transitions:
            return False

        return new_status in valid_transitions[user_role].get(current_status, [])

# Public QR Endpoints (No authentication required for customers)


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_qr_token(request):
    """Validate QR token and return table info"""
    serializer = QRValidationSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    qr_token = serializer.validated_data['qr_token']
    table_id = serializer.validated_data.get('table_id')

    try:
        if table_id:
            # Validate specific table with token
            table = Table.objects.get(
                id=table_id, qr_token=qr_token, is_active=True)
        else:
            # Find table by token only
            table = Table.objects.get(qr_token=qr_token, is_active=True)

        if not table.is_qr_valid():
            return Response({
                'valid': False,
                'message': 'QR code has expired. Please scan a fresh QR code.'
            }, status=status.HTTP_410_GONE)

        # Return table and restaurant info
        restaurant = table.branch.restaurant

        return Response({
            'valid': True,
            'table': {
                'id': table.id,
                'table_number': table.table_number,
                'table_name': table.table_name,
                'capacity': table.capacity,
                'branch_name': table.branch.name,
            },
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.name,
                'logo': restaurant.logo.url if restaurant.logo else None,
            }
        })

    except Table.DoesNotExist:
        return Response({
            'valid': False,
            'message': 'Invalid QR code or table not found.'
        }, status=status.HTTP_404_NOT_FOUND)

# Cart Management


class CartView(APIView):
    """Cart management for customers"""

    def get(self, request):
        """Get or create cart for session/table"""
        session_id = request.query_params.get('session_id')
        table_id = request.query_params.get('table_id')

        if not session_id or not table_id:
            return Response({'error': 'session_id and table_id required'}, status=400)

        try:
            table = Table.objects.get(id=table_id, is_active=True)
        except Table.DoesNotExist:
            return Response({'error': 'Table not found'}, status=404)

        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            session_id=session_id,
            table=table,
            is_active=True,
            defaults={'created_at': timezone.now()}
        )

        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def delete(self, request):
        """Clear cart"""
        session_id = request.query_params.get('session_id')
        table_id = request.query_params.get('table_id')

        if not session_id or not table_id:
            return Response({'error': 'session_id and table_id required'}, status=400)

        try:
            cart = Cart.objects.get(
                session_id=session_id,
                table_id=table_id,
                is_active=True
            )
            cart.is_active = False
            cart.save()
            return Response({'success': True, 'message': 'Cart cleared'})
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found'}, status=404)


@api_view(['POST'])
def add_to_cart(request):
    """Add item to cart"""
    serializer = CartAddItemSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    session_id = data.get('session_id')
    table_id = data.get('table_id')
    menu_item_id = data['menu_item_id']
    quantity = data['quantity']
    special_instructions = data.get('special_instructions', '')

    # Validate table and menu item
    try:
        table = Table.objects.get(id=table_id, is_active=True)
        menu_item = MenuItem.objects.get(id=menu_item_id, is_available=True)
    except (Table.DoesNotExist, MenuItem.DoesNotExist):
        return Response({'error': 'Invalid table or menu item'}, status=404)

    # Get or create cart
    cart, created = Cart.objects.get_or_create(
        session_id=session_id,
        table=table,
        is_active=True,
        defaults={'created_at': timezone.now()}
    )

    # Check if item already exists in cart
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        menu_item=menu_item,
        special_instructions=special_instructions,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    serializer = CartItemSerializer(cart_item)
    return Response(serializer.data, status=201 if created else 200)


@api_view(['PUT', 'DELETE'])
def update_cart_item(request, cart_item_id):
    """Update or remove cart item"""
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found'}, status=404)

    if request.method == 'PUT':
        serializer = CartUpdateItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        quantity = serializer.validated_data['quantity']

        if quantity == 0:
            cart_item.delete()
            return Response({'success': True, 'message': 'Item removed'})

        cart_item.quantity = quantity
        cart_item.save()
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data)

    elif request.method == 'DELETE':
        cart_item.delete()
        return Response({'success': True, 'message': 'Item removed'})

# Order Management


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for order management"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    # Restrict to staff only
    permission_classes = [IsCashierOrHigher]
   # filter_backends = [DjangoFilterBackend,
    #                  filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['table', 'status',
    #                  'order_type', 'is_paid', 'is_priority']

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.all()

        # Apply manual filters
        status = self.request.query_params.get('status')
        if status:
            status_list = status.split(',')
            queryset = queryset.filter(status__in=status_list)

        is_paid = self.request.query_params.get('is_paid')
        if is_paid:
            queryset = queryset.filter(is_paid=(is_paid.lower() == 'true'))

        return queryset.select_related(
            'table', 'waiter'
        ).prefetch_related(
            'items__menu_item'
        )

    search_fields = ['order_number', 'customer_name', 'table__table_number']
    ordering_fields = ['placed_at', 'total_amount', 'order_number']

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.all()

        # Filter based on user role
        if user.role == 'admin':
            return queryset

        elif user.role == 'manager':
            if user.restaurant:
                return queryset.filter(table__branch__restaurant=user.restaurant)

        elif user.role == 'chef':
            # Chef can see orders that need preparation
            return queryset.filter(
                status__in=['confirmed', 'preparing'],
                table__branch=user.branch
            )

        elif user.role == 'waiter':
            # Waiter can see orders from their branch
            return queryset.filter(table__branch=user.branch)

        return Order.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Create order. Supports both cart-based and item-based creation.

        For cart-based: Send {'cart_id': X, ...}
        For item-based: Use /create-with-items/ endpoint
        """
        # If cart_id is provided, use existing logic
        if 'cart_id' in request.data:
            return super().create(request, *args, **kwargs)

        # Otherwise, redirect to create-with-items endpoint
        # Or implement item-based creation here
        return Response({
            'error': 'For creating orders with items directly, use /create-with-items/ endpoint',
            'endpoint': '/api/tables/orders/create-with-items/',
            'required_fields': ['table', 'order_type', 'items']
        }, status=400)

    @action(detail=True, methods=['post'])
    def calculate_totals(self, request, pk=None):
        """Recalculate order totals"""
        order = self.get_object()
        order.calculate_totals()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsWaiterOrHigher])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        user = request.user

        serializer = OrderStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        # Validate status transition based on user role
        if not self.validate_status_transition(order.status, new_status, user.role):
            return Response({
                'error': f'Cannot change status from {order.status} to {new_status}'
            }, status=400)

        # Update status
        order.status = new_status

        # Set appropriate timestamps
        now = timezone.now()
        if new_status == 'confirmed':
            order.confirmed_at = now
            order.waiter = user
            order.requires_waiter_confirmation = False
        elif new_status == 'preparing':
            order.preparation_started_at = now
        elif new_status == 'ready':
            order.ready_at = now
        elif new_status == 'served':
            order.served_at = now
        elif new_status == 'completed':
            order.completed_at = now
            order.is_paid = True  # Auto-Mark as paid when completed
        elif new_status == 'cancelled':
            order.cancelled_at = now

        if notes:
            order.notes += f"\n{now}: {notes}" if order.notes else f"{now}: {notes}"

        order.save()

        from .utils import OrderManager
        OrderManager.update_table_status(order, new_status)

        return Response(OrderSerializer(order).data)

    def validate_status_transition(self, current_status, new_status, user_role):
        """Validate if status transition is allowed for user role"""
        valid_transitions = {
            'admin': {
                'pending': ['confirmed', 'cancelled'],
                'confirmed': ['preparing', 'cancelled'],
                'preparing': ['ready', 'cancelled'],
                'ready': ['served', 'cancelled'],
                'served': ['completed', 'cancelled'],
                'completed': [],
                'cancelled': [],
            },
            'manager': {
                'pending': ['confirmed', 'cancelled'],
                'confirmed': ['preparing', 'cancelled'],
                'preparing': ['ready', 'cancelled'],
                'ready': ['served', 'cancelled'],
                'served': ['completed', 'cancelled'],
                'completed': [],
                'cancelled': [],
            },
            'chef': {
                'pending': [],
                'confirmed': ['preparing'],
                'preparing': ['ready'],
                'ready': [],
                'served': [],
                'completed': [],
                'cancelled': [],
            },
            'waiter': {
                'pending': ['confirmed'],
                'confirmed': [],
                'preparing': [],
                'ready': ['served'],
                'served': ['completed'],
                'completed': [],
                'cancelled': [],
            },
        }

        if user_role not in valid_transitions:
            return False

        return new_status in valid_transitions[user_role].get(current_status, [])

    @action(detail=False, methods=['get'])
    def pending_confirmation(self, request):
        """Get orders pending waiter confirmation (QR orders)"""
        queryset = self.get_queryset().filter(
            status='pending',
            requires_waiter_confirmation=True
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsChefOrHigher])
    def kitchen_orders(self, request):
        """Get orders for kitchen display (confirmed & preparing)"""
        queryset = self.get_queryset().filter(
            status__in=['confirmed', 'preparing']
        ).order_by('is_priority', 'placed_at')

        # Serialize for kitchen display
        orders_data = []
        for order in queryset:
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'table_number': order.table.table_number if order.table else 'N/A',
                'items': [
                    {
                        'name': item.menu_item.name if item.menu_item else 'Unknown Item',  # FIXED HERE
                        'quantity': item.quantity,
                        'instructions': item.special_instructions,
                        'preparation_time': item.menu_item.preparation_time if item.menu_item else 15
                    }
                    for item in order.items.all()
                ],
                'status': order.status,
                'is_priority': order.is_priority,
                'placed_at': order.placed_at,
                'preparation_time': order.get_preparation_time(),
            })

        return Response(orders_data)

    @action(detail=False, methods=['get'])
    def by_table(self, request, table_id):
        """Get orders for a specific table"""
        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return Response({'error': 'Table not found'}, status=404)

        queryset = self.get_queryset().filter(table=table, status__in=[
            'pending', 'confirmed', 'preparing', 'ready'])
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_qr_order(request):
    """Submit QR order from customer (no authentication required)"""
    # This endpoint will be called from customer's mobile browser
    # It requires session_id, table_id, and cart items

    session_id = request.data.get('session_id')
    table_id = request.data.get('table_id')
    customer_name = request.data.get('customer_name', '')

    if not session_id or not table_id:
        return Response({'error': 'session_id and table_id required'}, status=400)

    try:
        table = Table.objects.get(id=table_id, is_active=True)
    except Table.DoesNotExist:
        return Response({'error': 'Table not found'}, status=404)

    # Get active cart for this session and table
    try:
        cart = Cart.objects.get(
            session_id=session_id,
            table_id=table_id,
            is_active=True
        )
    except Cart.DoesNotExist:
        return Response({'error': 'Cart is empty'}, status=400)

    if cart.item_count == 0:
        return Response({'error': 'Cart is empty'}, status=400)

    # Create order
    order = Order.objects.create(
        table=table,
        customer_name=customer_name,
        order_type='qr',
        status='pending',
        requires_waiter_confirmation=True
    )

    # Transfer cart items to order
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

    return Response({
        'success': True,
        'order_number': order.order_number,
        'message': 'Order submitted successfully. Waiting for waiter confirmation.',
        'order': OrderSerializer(order).data
    }, status=201)


# views for order creation

# Updated create_order_with_items view using serializer
# In tables/views.py

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order_with_items(request):
    """
    Professional endpoint for creating orders with items.

    Example POST:
    {
        "table": 1,
        "order_type": "waiter",
        "customer_name": "John Doe",
        "notes": "Extra napkins",
        "is_priority": false,
        "items": [
            {
                "menu_item": 1,
                "quantity": 2,
                "special_instructions": "No onions"
            }
        ]
    }
    """
    # Validate request data
    serializer = OrderWithItemsSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors,
            'message': 'Validation failed'
        }, status=400)

    data = serializer.validated_data

    try:
        # Get table
        table = Table.objects.get(id=data['table'])

        # Prepare additional kwargs
        order_kwargs = {
            'customer_name': data['customer_name'],
            'notes': data['notes'],
            'is_priority': data['is_priority']
        }

        # Add waiter for waiter orders
        if data['order_type'] == 'waiter':
            order_kwargs['waiter'] = request.user

        # Use OrderManager for consistency
        from .utils import OrderManager  # Create utils.py if needed

        order = OrderManager.create_order_with_items(
            table=table,
            order_type=data['order_type'],
            items_data=data['items'],
            **order_kwargs
        )

        # Return success response
        return Response({
            'success': True,
            'order': OrderSerializer(order).data,
            'message': f'Order #{order.order_number} created successfully'
        }, status=201)

    except Table.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Table not found'
        }, status=404)

    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)

    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"Error creating order: {e}")
        print(traceback.format_exc())

        return Response({
            'success': False,
            'error': 'Internal server error',
            'debug': str(e) if settings.DEBUG else None
        }, status=500)


# print fuction for orders

# Add to tables/views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_order(request, order_id):
    """Generate printable order receipt"""
    try:
        order = Order.objects.get(id=order_id)

        # Create HTML for printing
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .receipt {{ max-width: 400px; margin: 0 auto; }}
                .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }}
                .items {{ margin: 20px 0; }}
                .item {{ display: flex; justify-content: space-between; margin: 5px 0; }}
                .total {{ border-top: 2px solid #000; padding-top: 10px; margin-top: 20px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <h2>ORDER RECEIPT</h2>
                    <p>Order #{order.order_number}</p>
                    <p>Table: {order.table.table_number if order.table else 'N/A'}</p>
                    <p>Date: {order.placed_at.strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                
                <div class="items">
                    <h3>Items:</h3>
                    {''.join([f'<div class="item"><span>{item.quantity}x {item.menu_item.name}</span><span>${item.total_price:.2f}</span></div>' for item in order.items.all()])}
                </div>
                
                <div class="total">
                    <div class="item"><span>Subtotal:</span><span>${order.subtotal}</span></div>
                    <div class="item"><span>Tax:</span><span>${order.tax_amount}</span></div>
                    <div class="item"><span>Service:</span><span>${order.service_charge}</span></div>
                    <div class="item"><span>Total:</span><span>${order.total_amount}</span></div>
                </div>
                
                <div class="footer">
                    <p>Thank you for dining with us!</p>
                </div>
            </div>
        </body>
        </html>
        """

        return HttpResponse(html_content)

    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)


# ==================== UTILITIES ====================
# payment views

# In tables/views.py - Update the existing process_payment function
@api_view(['POST'])
@permission_classes([IsWaiterOrHigher])
def process_payment(request, order_id):
    """Process payment for an order - Now uses Payment model"""
    try:
        order = Order.objects.get(id=order_id)

        # Check if order is served
        if order.status != 'served':
            return Response({
                'error': f'Order must be served before payment. Current status: {order.status}'
            }, status=400)

        # Get payment data from request
        payment_method = request.data.get('payment_method', 'cash')
        amount_paid = request.data.get('amount_paid')
        customer_name = request.data.get('customer_name', order.customer_name)
        customer_phone = request.data.get('customer_phone', '')
        notes = request.data.get('notes', '')

        # If amount not specified, use order total
        if not amount_paid:
            amount_paid = order.total_amount

        # Import Payment model
        from payments.models import Payment

        # Create payment
        payment = Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=amount_paid,
            status='completed' if payment_method == 'cash' else 'pending',
            processed_by=request.user,
            customer_name=customer_name,
            customer_phone=customer_phone,
            notes=notes
        )

        # For cash payments, complete immediately
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

            # Update table status to cleaning
            if order.table:
                order.table.status = 'cleaning'
                order.table.save()

        # For digital payments, initiate payment
        elif payment_method in ['cbe', 'telebirr', 'cbe_wallet']:
            # This would initiate payment through gateway
            # For now, we'll just mark as pending
            pass

        return Response({
            'success': True,
            'payment_id': str(payment.payment_id),
            'order_number': order.order_number,
            'amount_paid': float(amount_paid),
            'payment_method': payment_method,
            'status': payment.status,
            'message': f'Payment {payment.status}.'
        })

    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# tables/views.py
@api_view(['POST'])
@permission_classes([IsWaiterOrHigher])
def present_bill(request, order_id):
    """Waiter presents bill to customer"""
    order = get_object_or_404(Order, id=order_id)

    # Validate: Order must be served
    if order.status != 'served':
        return Response({
            'error': f'Order must be served first. Current status: {order.status}'
        }, status=400)

    # Update status
    order.status = 'bill_presented'
    order.save()

    # Generate bill data
    bill_data = {
        'order_number': order.order_number,
        'table_number': order.table.table_number if order.table else 'N/A',
        'customer_name': order.customer_name,
        'total_amount': order.total_amount,
        'items': OrderItemSerializer(order.items.all(), many=True).data
    }

    return Response({
        'success': True,
        'message': 'Bill presented successfully',
        'bill': bill_data
    })


# detail tables orders views

@role_required(['waiter', 'manager', 'admin'])
def table_orders(request, table_id):
    """View orders for a specific table"""
    try:
        table = Table.objects.get(id=table_id)
    except Table.DoesNotExist:
        return HttpResponse("Table not found", status=404)

    context = {
        'user': request.user,
        'user_role': request.user.role,
        'table': table,
    }
    return render(request, 'waiter/table_orders.html', context)
