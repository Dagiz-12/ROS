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
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
import uuid
from django.http import HttpResponseForbidden


from .models import Table, Cart, CartItem, Order, OrderItem
from .serializers import (
    TableSerializer, TableCreateSerializer, CartSerializer, CartItemSerializer,
    OrderSerializer, OrderCreateSerializer, QRValidationSerializer,
    CartAddItemSerializer, CartUpdateItemSerializer, OrderStatusUpdateSerializer
)
from menu.models import MenuItem
from accounts.permissions import IsAdminUser, IsManagerOrAdmin, IsWaiterOrHigher


# ==================== HTML TEMPLATE VIEWS ====================

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render


def check_role(user, allowed_roles):
    """Check if user has one of the allowed roles"""
    return hasattr(user, 'role') and user.role in allowed_roles


def role_required(allowed_roles):
    """Decorator to check user role"""
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if not check_role(request.user, allowed_roles):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Permission denied")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

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
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
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
        new_status = request.data.get('status')

        if new_status in dict(Table.STATUS_CHOICES):
            table.status = new_status
            table.save()
            serializer = self.get_serializer(table)
            return Response(serializer.data)

        return Response({'error': 'Invalid status'}, status=400)

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
    permission_classes = [IsAuthenticated, IsWaiterOrHigher]
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

        return queryset

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
        """Create a new order"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # For QR orders, set requires_waiter_confirmation=True
        if serializer.validated_data.get('order_type') == 'qr':
            serializer.validated_data['requires_waiter_confirmation'] = True

        order = serializer.save()

        # Log the order creation
        # audit_log.delay(
        #     user_id=request.user.id if request.user.is_authenticated else None,
        #     action='CREATE',
        #     model_name='Order',
        #     object_id=order.id,
        #     details={'order_number': order.order_number}
        # )

        headers = self.get_success_headers(serializer.data)
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @action(detail=True, methods=['post'])
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
        elif new_status == 'cancelled':
            order.cancelled_at = now

        if notes:
            order.notes += f"\n{now}: {notes}" if order.notes else f"{now}: {notes}"

        order.save()

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

    @action(detail=False, methods=['get'])
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
                'table_number': order.table.table_number,
                'items': [
                    {
                        'name': item.menu_item.name,
                        'quantity': item.quantity,
                        'instructions': item.special_instructions
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


# debug views

# Add to core/views.py or tables/views.py


@login_required
def debug_auth(request):
    """Debug endpoint to check authentication status"""
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'role': request.user.role if hasattr(request.user, 'role') else None,
        'session_id': request.session.session_key,
        'has_session': hasattr(request, 'session') and request.session.session_key is not None,
        'cookies': dict(request.COOKIES),
        'headers': dict(request.headers),
    })

# Add to urls.py
# path('debug-auth/', debug_auth, name='debug-auth'),
