from accounts.permissions import IsManagerOrAdmin, IsWaiterOrHigher
from accounts.authentication import JWTAuthentication
from .serializers import StockTransactionSerializer
from .models import StockTransaction, StockItem, Recipe, StockAlert, InventoryReport
from tables.models import Order, OrderItem
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from decimal import Decimal

from django.db.models import Sum, Count, Avg, F, DecimalField, ExpressionWrapper


from .models import StockItem, StockTransaction, StockAlert, Recipe, InventoryReport
from .serializers import (
    StockItemSerializer, StockTransactionSerializer,
    StockAlertSerializer, RecipeSerializer, InventoryReportSerializer
)
from accounts.permissions import IsManagerOrAdmin, IsWaiterOrHigher


class StockItemViewSet(viewsets.ModelViewSet):
    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = StockItem.objects.all()

        # Filter by restaurant/branch based on user role
        if user.role in ['admin', 'manager']:
            if user.restaurant:
                queryset = queryset.filter(restaurant=user.restaurant)
                if user.branch:
                    queryset = queryset.filter(branch=user.branch)
        else:
            # Other roles can only view
            queryset = queryset.filter(
                restaurant=user.restaurant, branch=user.branch)

        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            queryset = queryset.filter(
                current_quantity__lte=F('minimum_quantity'))

        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Adjust stock quantity (positive or negative)"""
        stock_item = self.get_object()
        quantity = Decimal(request.data.get('quantity', 0))
        reason = request.data.get('reason', 'Manual adjustment')

        if quantity == 0:
            return Response({'error': 'Quantity cannot be zero'}, status=status.HTTP_400_BAD_REQUEST)

        transaction_type = 'adjustment'
        if quantity > 0:
            stock_item.current_quantity += quantity
        else:
            if abs(quantity) > stock_item.current_quantity:
                return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
            stock_item.current_quantity += quantity  # quantity is negative
            transaction_type = 'waste' if 'waste' in reason.lower() else 'adjustment'

        stock_item.save()

        # Create transaction
        StockTransaction.objects.create(
            stock_item=stock_item,
            transaction_type=transaction_type,
            quantity=abs(quantity),
            unit_cost=stock_item.cost_per_unit,
            total_cost=abs(quantity) * stock_item.cost_per_unit,
            reason=reason,
            user=request.user,
            restaurant=stock_item.restaurant,
            branch=stock_item.branch
        )

        return Response({'message': 'Stock adjusted successfully', 'new_quantity': stock_item.current_quantity})


class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = StockTransaction.objects.all()

        if user.restaurant:
            queryset = queryset.filter(restaurant=user.restaurant)
            if user.branch:
                queryset = queryset.filter(branch=user.branch)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)

        # Filter by type
        transaction_type = self.request.query_params.get('type', None)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        return queryset


class StockAlertViewSet(viewsets.ModelViewSet):
    queryset = StockAlert.objects.all()
    serializer_class = StockAlertSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = StockAlert.objects.filter(
            resolved=False)  # Show only unresolved by default

        if user.restaurant:
            queryset = queryset.filter(restaurant=user.restaurant)
            if user.branch:
                queryset = queryset.filter(branch=user.branch)

        # Show resolved if requested
        show_resolved = self.request.query_params.get('show_resolved', 'false')
        if show_resolved == 'true':
            queryset = StockAlert.objects.all()
            if user.restaurant:
                queryset = queryset.filter(restaurant=user.restaurant)
                if user.branch:
                    queryset = queryset.filter(branch=user.branch)

        return queryset

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.resolve(request.user)
        return Response({'message': 'Alert resolved'})


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.all()

        # Filter by restaurant through menu item
        if user.restaurant:
            queryset = queryset.filter(
                menu_item__category__restaurant=user.restaurant)

        # Filter by menu item
        menu_item_id = self.request.query_params.get('menu_item_id', None)
        if menu_item_id:
            queryset = queryset.filter(menu_item_id=menu_item_id)

        return queryset


class InventoryReportViewSet(viewsets.ModelViewSet):
    queryset = InventoryReport.objects.all()
    serializer_class = InventoryReportSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = InventoryReport.objects.all()

        if user.restaurant:
            queryset = queryset.filter(restaurant=user.restaurant)
            if user.branch:
                queryset = queryset.filter(branch=user.branch)

        return queryset


# Custom API Views


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def low_stock_items(request):
    """Get all low stock items"""
    user = request.user
    queryset = StockItem.objects.filter(is_active=True)

    if user.restaurant:
        queryset = queryset.filter(restaurant=user.restaurant)
        if user.branch:
            queryset = queryset.filter(branch=user.branch)

    low_stock = queryset.filter(current_quantity__lte=F('minimum_quantity'))
    serializer = StockItemSerializer(low_stock, many=True)

    return Response({
        'count': low_stock.count(),
        'items': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def total_stock_value(request):
    """Calculate total value of all stock"""
    user = request.user
    queryset = StockItem.objects.filter(is_active=True)

    if user.restaurant:
        queryset = queryset.filter(restaurant=user.restaurant)
        if user.branch:
            queryset = queryset.filter(branch=user.branch)

    total_value = queryset.aggregate(
        total=Sum(F('current_quantity') * F('cost_per_unit'),
                  output_field=DecimalField())
    )['total'] or Decimal('0.00')

    item_count = queryset.count()
    low_stock_count = queryset.filter(
        current_quantity__lte=F('minimum_quantity')).count()

    return Response({
        'total_stock_value': total_value,
        'item_count': item_count,
        'low_stock_count': low_stock_count,
        'currency': 'ETB'
    })


# Add these views to inventory/views.py


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def waste_analysis(request):
    """
    Analyze waste transactions for a given period
    """
    user = request.user

    # Get date range from query parameters
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    # Filter transactions
    queryset = StockTransaction.objects.filter(
        transaction_type='waste',
        transaction_date__gte=start_date
    )

    if user.restaurant:
        queryset = queryset.filter(restaurant=user.restaurant)
        if user.branch:
            queryset = queryset.filter(branch=user.branch)

    # Aggregate waste data
    waste_by_item = queryset.values(
        'stock_item__name',
        'stock_item__unit',
        'stock_item__category'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum('total_cost'),
        transaction_count=Count('id')
    ).order_by('-total_cost')

    # Daily waste trend
    daily_waste = queryset.annotate(
        date=TruncDate('transaction_date')
    ).values('date').annotate(
        daily_cost=Sum('total_cost'),
        daily_quantity=Sum('quantity')
    ).order_by('date')

    # Top waste reasons
    waste_reasons = queryset.exclude(reason='').values('reason').annotate(
        count=Count('id'),
        total_cost=Sum('total_cost')
    ).order_by('-total_cost')[:10]

    return Response({
        'success': True,
        'period': {
            'start_date': start_date.date(),
            'end_date': timezone.now().date(),
            'days': days
        },
        'summary': {
            'total_waste_cost': queryset.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00'),
            'total_waste_quantity': queryset.aggregate(total=Sum('quantity'))['total'] or Decimal('0.00'),
            'transaction_count': queryset.count()
        },
        'waste_by_item': list(waste_by_item),
        'daily_trend': list(daily_waste),
        'top_reasons': list(waste_reasons)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def generate_report(request):
    """
    Generate an inventory report
    """
    user = request.user

    report_type = request.data.get('report_type', 'daily')
    start_date_str = request.data.get('start_date')
    end_date_str = request.data.get('end_date')

    # Parse dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date(
    ) if start_date_str else timezone.now().date() - timedelta(days=7)
    end_date = datetime.strptime(
        end_date_str, '%Y-%m-%d').date() if end_date_str else timezone.now().date()

    # Filter based on restaurant/branch
    stock_items = StockItem.objects.filter(is_active=True)
    transactions = StockTransaction.objects.all()

    if user.restaurant:
        stock_items = stock_items.filter(restaurant=user.restaurant)
        transactions = transactions.filter(restaurant=user.restaurant)
        if user.branch:
            stock_items = stock_items.filter(branch=user.branch)
            transactions = transactions.filter(branch=user.branch)

    # Filter transactions by date range
    transactions = transactions.filter(
        transaction_date__range=[start_date, end_date]
    )

    report_data = {}

    if report_type == 'stock_valuation':
        # Stock valuation report
        stock_items_data = []
        for item in stock_items:
            stock_items_data.append({
                'name': item.name,
                'category': item.category,
                'current_quantity': float(item.current_quantity),
                'unit': item.unit,
                'cost_per_unit': float(item.cost_per_unit),
                'stock_value': float(item.stock_value),
                'is_low_stock': item.is_low_stock,
                'needs_reorder': item.needs_reorder
            })

        total_value = sum(item['stock_value'] for item in stock_items_data)
        low_stock_count = sum(
            1 for item in stock_items_data if item['is_low_stock'])

        report_data = {
            'report_type': 'stock_valuation',
            'stock_items': stock_items_data,
            'summary': {
                'total_items': len(stock_items_data),
                'total_value': total_value,
                'low_stock_count': low_stock_count,
                'average_item_value': total_value / len(stock_items_data) if stock_items_data else 0
            }
        }

    elif report_type == 'transaction_summary':
        # Transaction summary report
        transactions_by_type = transactions.values('transaction_type').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity'),
            total_cost=Sum('total_cost')
        )

        daily_transactions = transactions.annotate(
            date=TruncDate('transaction_date')
        ).values('date').annotate(
            transaction_count=Count('id'),
            daily_cost=Sum('total_cost')
        ).order_by('date')

        top_items = transactions.values(
            'stock_item__name',
            'stock_item__category'
        ).annotate(
            transaction_count=Count('id'),
            total_quantity=Sum('quantity'),
            total_cost=Sum('total_cost')
        ).order_by('-total_cost')[:10]

        report_data = {
            'report_type': 'transaction_summary',
            'transactions_by_type': list(transactions_by_type),
            'daily_transactions': list(daily_transactions),
            'top_items': list(top_items),
            'summary': {
                'total_transactions': transactions.count(),
                'total_quantity': transactions.aggregate(total=Sum('quantity'))['total'] or Decimal('0.00'),
                'total_cost': transactions.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')
            }
        }

    elif report_type == 'waste_analysis':
        # Waste analysis report
        waste_transactions = transactions.filter(transaction_type='waste')

        waste_by_item = waste_transactions.values(
            'stock_item__name',
            'stock_item__category'
        ).annotate(
            waste_count=Count('id'),
            total_quantity=Sum('quantity'),
            total_cost=Sum('total_cost')
        ).order_by('-total_cost')

        waste_reasons = waste_transactions.exclude(reason='').values('reason').annotate(
            count=Count('id'),
            total_cost=Sum('total_cost')
        ).order_by('-total_cost')[:10]

        report_data = {
            'report_type': 'waste_analysis',
            'waste_by_item': list(waste_by_item),
            'waste_reasons': list(waste_reasons),
            'summary': {
                'total_waste_cost': waste_transactions.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00'),
                'total_waste_quantity': waste_transactions.aggregate(total=Sum('quantity'))['total'] or Decimal('0.00'),
                'waste_transaction_count': waste_transactions.count()
            }
        }

    # Create report record
    from .models import InventoryReport
    report = InventoryReport.objects.create(
        report_type=report_type,
        title=f"{report_type.replace('_', ' ').title()} Report - {start_date} to {end_date}",
        data=report_data,
        summary=f"Generated {report_type} report covering {start_date} to {end_date}",
        start_date=start_date,
        end_date=end_date,
        generated_by=user,
        restaurant=user.restaurant,
        branch=user.branch if user.branch else None
    )

    return Response({
        'success': True,
        'report_id': report.id,
        'title': report.title,
        'generated_at': report.created_at,
        'data': report_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def auto_deduct_from_order(request, order_id):
    """
    Manually trigger inventory deduction for a specific order
    (Useful for testing or fixing issues)
    """
    try:
        order = Order.objects.get(id=order_id)

        # Check permissions - user must have access to this order's restaurant/branch
        if request.user.restaurant and order.table.branch.restaurant != request.user.restaurant:
            return Response({'error': 'Unauthorized access to this order'}, status=status.HTTP_403_FORBIDDEN)

        if request.user.branch and order.table.branch != request.user.branch:
            return Response({'error': 'Unauthorized access to this order'}, status=status.HTTP_403_FORBIDDEN)

        # Check if already deducted
        if order.inventory_deducted:
            return Response({
                'success': True,
                'message': 'Inventory already deducted for this order',
                'order_id': order_id,
                'inventory_deducted': True
            })

        # Check if order is completed
        if order.status != 'completed':
            return Response({
                'success': False,
                'error': f'Order must be completed to deduct inventory. Current status: {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Import the deduction function
        from .signals import deduct_inventory_from_order

        # Deduct inventory
        deduct_inventory_from_order(order)

        # Refresh order from database
        order.refresh_from_db()

        return Response({
            'success': True,
            'message': 'Inventory deducted successfully',
            'order_id': order_id,
            'order_number': order.order_number,
            'inventory_deducted': order.inventory_deducted,
            'status': order.status
        })

    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
