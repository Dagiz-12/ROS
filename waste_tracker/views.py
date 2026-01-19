# waste_tracker/views.py
from accounts.decorators import role_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import WasteCategory, WasteReason, WasteRecord, WasteTarget, WasteAlert
from .serializers import (
    WasteCategorySerializer, WasteReasonSerializer,
    WasteRecordSerializer, WasteRecordCreateSerializer,
    WasteTargetSerializer, WasteAlertSerializer,
    WasteDashboardSerializer, WasteAnalyticsSerializer
)
from .business_logic import EnhancedWasteAnalyzer, WasteAlertManager
from accounts.permissions import IsManagerOrAdmin, IsWaiterOrHigher, IsChefOrHigher
from inventory.models import StockItem


class WasteCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for waste categories
    Access: Managers and Admins only
    """
    queryset = WasteCategory.objects.all()
    serializer_class = WasteCategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, IsWaiterOrHigher]
        else:
            permission_classes = [IsAuthenticated, IsManagerOrAdmin]
        return [permission() for permission in permission_classes]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category_type', 'is_active', 'requires_approval']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'sort_order', 'created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = WasteCategory.objects.all()

        # Filter by restaurant
        if user.restaurant:
            queryset = queryset.filter(restaurant=user.restaurant)

        return queryset

    def perform_create(self, serializer):
        # Automatically set restaurant from user
        serializer.save(restaurant=self.request.user.restaurant)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a waste category"""
        category = self.get_object()

        # Last 30 days statistics
        thirty_days_ago = timezone.now() - timedelta(days=30)

        waste_records = WasteRecord.objects.filter(
            waste_reason__category=category,
            status='approved',
            recorded_at__gte=thirty_days_ago
        )

        total_cost = Decimal('0.00')
        record_count = waste_records.count()

        for record in waste_records:
            if record.stock_transaction:
                total_cost += record.stock_transaction.total_cost

        # Top reasons in this category
        top_reasons = waste_records.values(
            'waste_reason__name',
            'waste_reason__controllability'
        ).annotate(
            count=Count('id'),
            total_cost=Sum('stock_transaction__total_cost')
        ).order_by('-total_cost')[:5]

        return Response({
            'category_id': category.id,
            'category_name': category.name,
            'period_days': 30,
            'statistics': {
                'total_records': record_count,
                'total_cost': float(total_cost),
                'avg_cost_per_record': float(total_cost / record_count) if record_count > 0 else 0,
                'daily_avg_cost': float(total_cost / 30)
            },
            'top_reasons': list(top_reasons),
            'controllability_breakdown': {
                'controllable': waste_records.filter(waste_reason__controllability='controllable').count(),
                'partially_controllable': waste_records.filter(waste_reason__controllability='partially_controllable').count(),
                'uncontrollable': waste_records.filter(waste_reason__controllability='uncontrollable').count()
            }
        })


class WasteReasonViewSet(viewsets.ModelViewSet):
    """
    API endpoint for waste reasons
    Access: Managers and Admins only
    """
    queryset = WasteReason.objects.all()
    serializer_class = WasteReasonSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list', 'retrieve']:
            # Allow waiters and above to view waste reasons
            permission_classes = [IsAuthenticated, IsWaiterOrHigher]
        else:
            # Only managers and admins can create/edit/delete reasons
            permission_classes = [IsAuthenticated, IsManagerOrAdmin]
        return [permission() for permission in permission_classes]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'controllability',
                        'is_active', 'requires_explanation', 'requires_photo']
    search_fields = ['name', 'description']

    def get_queryset(self):
        user = self.request.user
        queryset = WasteReason.objects.all()

        # Filter by restaurant through category
        if user.restaurant:
            queryset = queryset.filter(category__restaurant=user.restaurant)

        # Filter by category if provided
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset

    @action(detail=True, methods=['get'])
    def usage_statistics(self, request, pk=None):
        """Get usage statistics for a waste reason"""
        reason = self.get_object()

        # Last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)

        waste_records = WasteRecord.objects.filter(
            waste_reason=reason,
            status='approved',
            recorded_at__gte=thirty_days_ago
        )

        total_cost = Decimal('0.00')
        total_quantity = Decimal('0.00')
        record_count = waste_records.count()

        for record in waste_records:
            if record.stock_transaction:
                total_cost += record.stock_transaction.total_cost
                total_quantity += record.stock_transaction.quantity

        # Top items wasted with this reason
        top_items = waste_records.values(
            'stock_transaction__stock_item__name',
            'stock_transaction__stock_item__category'
        ).annotate(
            count=Count('id'),
            total_cost=Sum('stock_transaction__total_cost'),
            total_quantity=Sum('stock_transaction__quantity')
        ).order_by('-total_cost')[:5]

        # Staff who recorded this waste
        top_staff = waste_records.values(
            'recorded_by__username',
            'recorded_by__id'
        ).annotate(
            count=Count('id'),
            total_cost=Sum('stock_transaction__total_cost')
        ).order_by('-total_cost')[:5]

        return Response({
            'reason_id': reason.id,
            'reason_name': reason.name,
            'period_days': 30,
            'statistics': {
                'total_records': record_count,
                'total_cost': float(total_cost),
                'total_quantity': float(total_quantity),
                'avg_cost_per_record': float(total_cost / record_count) if record_count > 0 else 0,
                'avg_quantity_per_record': float(total_quantity / record_count) if record_count > 0 else 0
            },
            'top_items': list(top_items),
            'top_staff': list(top_staff),
            'alerts_generated': WasteAlert.objects.filter(
                waste_reason=reason,
                created_at__gte=thirty_days_ago
            ).count()
        })


class WasteRecordViewSet(viewsets.ModelViewSet):
    """
    API endpoint for waste records
    Access: Chefs and above can view, Managers and Admins can manage
    """
    queryset = WasteRecord.objects.all()
    permission_classes = [IsAuthenticated, IsWaiterOrHigher]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority',
                        'branch', 'waste_reason', 'station', 'shift']
    search_fields = ['notes', 'corrective_action',
                     'waste_source', 'batch_number']
    ordering_fields = ['created_at', 'total_cost', 'priority']
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        # Use simplified serializer for creation (employee interface)
        if self.action == 'create':
            return WasteRecordCreateSerializer
        return WasteRecordSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = WasteRecord.objects.all()

        # Filter by restaurant/branch based on role
        if user.restaurant:
            queryset = queryset.filter(branch__restaurant=user.restaurant)

            if user.branch:
                queryset = queryset.filter(branch=user.branch)

        # Employees can only see their own records unless manager/admin
        if user.role in ['waiter', 'chef', 'cashier']:
            queryset = queryset.filter(recorded_by=user)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(recorded_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__date__lte=end_date)

        # Filter by stock item
        stock_item_id = self.request.query_params.get('stock_item_id')
        if stock_item_id:
            queryset = queryset.filter(
                stock_transaction__stock_item_id=stock_item_id)

        return queryset

    def perform_create(self, serializer):
        # Automatically set recorded_by to current user
        waste_record = serializer.save(
            recorded_by=self.request.user,
            branch=self.request.user.branch,
            recorded_at=timezone.now()
        )

        # Check if approval is required
        if waste_record.waste_reason.category.requires_approval:
            waste_record.status = 'pending'
            waste_record.save()

        # Check for recurring issues
        if waste_record.is_recurring_issue:
            # Create recurring issue alert
            WasteAlert.objects.create(
                alert_type='recurring_issue',
                title=f'Recurring Waste Issue: {waste_record.stock_item.name if waste_record.stock_item else "Unknown Item"}',
                message=f'This appears to be a recurring issue. {waste_record.waste_reason.name} '
                f'has occurred multiple times recently.',
                waste_record=waste_record,
                branch=waste_record.branch
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a waste record (Manager/Admin only)"""
        if not request.user.role in ['manager', 'admin']:
            return Response(
                {'error': 'Only managers and admins can approve waste records'},
                status=status.HTTP_403_FORBIDDEN
            )

        waste_record = self.get_object()
        notes = request.data.get('notes', '')

        waste_record.approve(request.user, notes)

        return Response({
            'success': True,
            'message': 'Waste record approved successfully',
            'record_id': waste_record.id,
            'status': waste_record.status,
            'reviewed_by': request.user.username
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a waste record (Manager/Admin only)"""
        if not request.user.role in ['manager', 'admin']:
            return Response(
                {'error': 'Only managers and admins can reject waste records'},
                status=status.HTTP_403_FORBIDDEN
            )

        waste_record = self.get_object()
        reason = request.data.get('reason', '')

        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        waste_record.reject(request.user, reason)

        return Response({
            'success': True,
            'message': 'Waste record rejected',
            'record_id': waste_record.id,
            'status': waste_record.status
        })

    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """Get all waste records pending approval"""
        queryset = self.get_queryset().filter(status='pending')

        # For non-managers/admins, only show their own pending records
        if request.user.role in ['waiter', 'chef', 'cashier']:
            queryset = queryset.filter(recorded_by=request.user)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_records(self, request):
        """Get waste records recorded by current user"""
        queryset = self.get_queryset().filter(recorded_by=request.user)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recurring_issues(self, request):
        """Get recurring waste issues"""
        from datetime import timedelta

        thirty_days_ago = timezone.now() - timedelta(days=30)

        # Find items with multiple waste records
        recurring = WasteRecord.objects.filter(
            status='approved',
            recorded_at__gte=thirty_days_ago,
            is_recurring_issue=True
        )

        # Group by recurrence_id
        grouped = {}
        for record in recurring:
            if record.recurrence_id:
                key = str(record.recurrence_id)
                if key not in grouped:
                    grouped[key] = {
                        'records': [],
                        'total_cost': Decimal('0.00'),
                        'first_occurrence': record.recorded_at,
                        'last_occurrence': record.recorded_at
                    }
                grouped[key]['records'].append(record)
                if record.stock_transaction:
                    grouped[key]['total_cost'] += record.stock_transaction.total_cost

                if record.recorded_at < grouped[key]['first_occurrence']:
                    grouped[key]['first_occurrence'] = record.recorded_at
                if record.recorded_at > grouped[key]['last_occurrence']:
                    grouped[key]['last_occurrence'] = record.recorded_at

        # Format response
        result = []
        for recurrence_id, data in grouped.items():
            if len(data['records']) >= 2:  # At least 2 records to be recurring
                first_record = data['records'][0]
                result.append({
                    'recurrence_id': recurrence_id,
                    'occurrence_count': len(data['records']),
                    'total_cost': float(data['total_cost']),
                    'first_occurrence': data['first_occurrence'],
                    'last_occurrence': data['last_occurrence'],
                    'days_between': (data['last_occurrence'] - data['first_occurrence']).days,
                    'item_name': first_record.stock_item.name if first_record.stock_item else 'Unknown',
                    'reason_name': first_record.waste_reason.name,
                    'stations': list(set(r.station for r in data['records'] if r.station)),
                    'staff_involved': list(set(r.recorded_by.username for r in data['records']))
                })

        return Response({
            'period_days': 30,
            'total_recurring_issues': len(result),
            'issues': sorted(result, key=lambda x: x['total_cost'], reverse=True)
        })


class WasteTargetViewSet(viewsets.ModelViewSet):
    """
    API endpoint for waste reduction targets
    Access: Managers and Admins only
    """
    queryset = WasteTarget.objects.all()
    serializer_class = WasteTargetSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active', 'period', 'target_type', 'branch']
    search_fields = ['name']

    def get_queryset(self):
        user = self.request.user
        queryset = WasteTarget.objects.all()

        if user.restaurant:
            queryset = queryset.filter(restaurant=user.restaurant)
            if user.branch:
                queryset = queryset.filter(branch=user.branch)

        return queryset

    def perform_create(self, serializer):
        serializer.save(restaurant=self.request.user.restaurant)

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update current progress for a target"""
        target = self.get_object()

        # Recalculate current value
        target.calculate_current_value()
        target.save()

        return Response({
            'success': True,
            'target_id': target.id,
            'current_value': float(target.current_value),
            'progress_percentage': float(target.progress_percentage),
            'is_on_track': target.is_on_track
        })

    @action(detail=False, methods=['get'])
    def active_targets(self, request):
        """Get all active waste reduction targets"""
        queryset = self.get_queryset().filter(is_active=True)

        # Calculate progress for each target
        targets_with_progress = []
        for target in queryset:
            target.calculate_current_value()
            targets_with_progress.append({
                'id': target.id,
                'name': target.name,
                'target_type': target.target_type,
                'target_value': float(target.target_value),
                'current_value': float(target.current_value),
                'progress_percentage': float(target.progress_percentage),
                'is_on_track': target.is_on_track,
                'period': target.period,
                'days_remaining': target.end_date - timezone.now().date() if target.end_date else None
            })

        return Response({
            'active_targets': len(targets_with_progress),
            'targets': targets_with_progress
        })


class WasteAlertViewSet(viewsets.ModelViewSet):
    """
    API endpoint for waste alerts
    Access: Chefs and above
    """
    queryset = WasteAlert.objects.all()
    serializer_class = WasteAlertSerializer
    permission_classes = [IsAuthenticated, IsChefOrHigher]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    # filterset_fields = ['alert_type', 'is_resolved', 'is_read', 'branch']  # Temporarily removed due to django_filters issue
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = WasteAlert.objects.all()

        if user.restaurant:
            queryset = queryset.filter(branch__restaurant=user.restaurant)
            if user.branch:
                queryset = queryset.filter(branch=user.branch)

        # By default, show unresolved alerts
        show_resolved = self.request.query_params.get('show_resolved', 'false')
        if show_resolved != 'true':
            queryset = queryset.filter(is_resolved=False)

        return queryset

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark an alert as read"""
        alert = self.get_object()
        alert.is_read = True
        alert.save()

        return Response({
            'success': True,
            'alert_id': alert.id,
            'is_read': alert.is_read
        })

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert (Manager/Admin only)"""
        if not request.user.role in ['manager', 'admin']:
            return Response(
                {'error': 'Only managers and admins can resolve alerts'},
                status=status.HTTP_403_FORBIDDEN
            )

        alert = self.get_object()
        notes = request.data.get('notes', '')

        alert.resolve(request.user, notes)

        return Response({
            'success': True,
            'alert_id': alert.id,
            'is_resolved': alert.is_resolved,
            'resolved_by': request.user.username,
            'resolved_at': alert.resolved_at
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread alerts"""
        queryset = self.get_queryset()
        unread_count = queryset.filter(is_read=False).count()

        return Response({
            'unread_count': unread_count,
            'total_alerts': queryset.count()
        })


# Custom API Views for Waste Dashboard and Analytics

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsChefOrHigher])
def waste_dashboard(request):
    """
    Get comprehensive waste dashboard data
    """
    user = request.user

    # Get date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Base queryset
    queryset = WasteRecord.objects.filter(branch__restaurant=user.restaurant)
    if user.branch:
        queryset = queryset.filter(branch=user.branch)

    # Calculate summary statistics
    today_waste = Decimal('0.00')
    week_waste = Decimal('0.00')
    month_waste = Decimal('0.00')

    # Today's waste
    today_records = queryset.filter(
        status='approved',
        recorded_at__date=today
    )
    for record in today_records:
        if record.stock_transaction:
            today_waste += record.stock_transaction.total_cost

    # Week's waste
    week_records = queryset.filter(
        status='approved',
        recorded_at__date__gte=week_ago
    )
    for record in week_records:
        if record.stock_transaction:
            week_waste += record.stock_transaction.total_cost

    # Month's waste
    month_records = queryset.filter(
        status='approved',
        recorded_at__date__gte=month_ago
    )
    for record in month_records:
        if record.stock_transaction:
            month_waste += record.stock_transaction.total_cost

    # Pending reviews
    pending_reviews = queryset.filter(status='pending').count()

    # Recurring issues
    recurring_issues = queryset.filter(
        is_recurring_issue=True,
        recorded_at__date__gte=week_ago
    ).count()

    # Waste by category
    waste_by_category = []
    categories = WasteCategory.objects.filter(
        restaurant=user.restaurant, is_active=True)

    for category in categories:
        category_records = queryset.filter(
            waste_reason__category=category,
            status='approved',
            recorded_at__date__gte=month_ago
        )

        category_cost = Decimal('0.00')
        for record in category_records:
            if record.stock_transaction:
                category_cost += record.stock_transaction.total_cost

        if category_records.exists():
            waste_by_category.append({
                'category_id': category.id,
                'category_name': category.name,
                'category_type': category.category_type,
                'waste_count': category_records.count(),
                'total_cost': float(category_cost),
                'color': category.color_code
            })

    # Recent waste (last 10 records)
    recent_waste = []
    recent_records = queryset.order_by('-recorded_at')[:10]
    for record in recent_records:
        recent_waste.append({
            'id': record.id,
            'item_name': record.stock_item.name if record.stock_item else 'Unknown',
            'quantity': float(record.quantity) if record.quantity else 0,
            'unit': record.stock_item.unit if record.stock_item else '',
            'reason': record.waste_reason.name,
            'cost': float(record.total_cost),
            'status': record.status,
            'recorded_by': record.recorded_by.username,
            'recorded_at': record.recorded_at,
            'station': record.station
        })

    # Active alerts
    alerts_queryset = WasteAlert.objects.filter(
        branch__restaurant=user.restaurant)
    if user.branch:
        alerts_queryset = alerts_queryset.filter(branch=user.branch)

    active_alerts = alerts_queryset.filter(
        is_resolved=False).order_by('-created_at')[:5]
    alerts_list = []
    for alert in active_alerts:
        alerts_list.append({
            'id': alert.id,
            'type': alert.alert_type,
            'title': alert.title,
            'message': alert.message,
            'created_at': alert.created_at,
            'is_read': alert.is_read
        })

    # Targets progress
    targets_queryset = WasteTarget.objects.filter(
        restaurant=user.restaurant,
        is_active=True
    )
    if user.branch:
        targets_queryset = targets_queryset.filter(branch=user.branch)

    targets_progress = []
    for target in targets_queryset:
        target.calculate_current_value()
        targets_progress.append({
            'id': target.id,
            'name': target.name,
            'target_type': target.target_type,
            'target_value': float(target.target_value),
            'current_value': float(target.current_value),
            'progress_percentage': float(target.progress_percentage),
            'is_on_track': target.is_on_track,
            'period': target.period
        })

    return Response({
        'success': True,
        'timestamp': timezone.now(),
        'summary': {
            'total_waste_cost_today': float(today_waste),
            'total_waste_cost_week': float(week_waste),
            'total_waste_cost_month': float(month_waste),
            'pending_reviews': pending_reviews,
            'recurring_issues': recurring_issues
        },
        'waste_by_category': waste_by_category,
        'recent_waste': recent_waste,
        'active_alerts': alerts_list,
        'targets_progress': targets_progress
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def detailed_waste_analytics(request):
    """
    Get detailed waste analytics
    """
    user = request.user

    # Get query parameters
    days = int(request.query_params.get('days', 30))
    branch_id = request.query_params.get('branch_id')

    if branch_id and user.role == 'manager':
        # Managers can only access their branch
        if user.branch and str(user.branch.id) != branch_id:
            return Response(
                {'error': 'Unauthorized access to this branch'},
                status=status.HTTP_403_FORBIDDEN
            )

    # Use the enhanced waste analyzer
    analytics = EnhancedWasteAnalyzer.analyze_detailed_waste_period(
        days=days,
        branch_id=branch_id
    )

    return Response({
        'success': True,
        'analytics': analytics
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def waste_reduction_potential(request):
    """
    Calculate waste reduction potential
    """
    user = request.user
    branch_id = request.query_params.get('branch_id')

    if branch_id and user.role == 'manager':
        if user.branch and str(user.branch.id) != branch_id:
            return Response(
                {'error': 'Unauthorized access to this branch'},
                status=status.HTTP_403_FORBIDDEN
            )

    potential = EnhancedWasteAnalyzer.calculate_waste_reduction_potential(
        branch_id=branch_id
    )

    return Response({
        'success': True,
        'reduction_potential': potential
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def waste_forecast(request):
    """
    Generate waste forecast
    """
    user = request.user
    days = int(request.query_params.get('days', 30))
    branch_id = request.query_params.get('branch_id')

    if branch_id and user.role == 'manager':
        if user.branch and str(user.branch.id) != branch_id:
            return Response(
                {'error': 'Unauthorized access to this branch'},
                status=status.HTTP_403_FORBIDDEN
            )

    forecast = EnhancedWasteAnalyzer.generate_waste_forecast(
        days=days,
        branch_id=branch_id
    )

    return Response({
        'success': True,
        'forecast': forecast
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsWaiterOrHigher])
def quick_waste_entry(request):
    """
    Quick waste entry for kitchen staff (mobile interface)
    """
    user = request.user

    # Try to get data from serializer first
    try:
        # Use the WasteRecordCreateSerializer to validate and create the record
        serializer = WasteRecordCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            # Create the waste record using serializer
            waste_record = serializer.save()

            # Set additional fields
            waste_record.recorded_by = user
            waste_record.branch = user.branch
            waste_record.recorded_at = timezone.now()
            waste_record.waste_occurred_at = timezone.now()
            waste_record.save()

            # Check if approval is required
            if waste_record.waste_reason.category.requires_approval:
                waste_record.status = 'pending'
                waste_record.save()

            # Check for recurring issues
            if waste_record.is_recurring_issue:
                # Create recurring issue alert
                WasteAlert.objects.create(
                    alert_type='recurring_issue',
                    title=f'Recurring Waste Issue: {waste_record.stock_item.name if waste_record.stock_item else "Unknown Item"}',
                    message=f'This appears to be a recurring issue. {waste_record.waste_reason.name} '
                    f'has occurred multiple times recently.',
                    waste_record=waste_record,
                    branch=waste_record.branch
                )

            return Response({
                'success': True,
                'waste_record_id': waste_record.id,
                'message': 'Waste recorded successfully',
                'details': {
                    'item_name': waste_record.stock_item.name if waste_record.stock_item else 'Unknown',
                    'quantity': float(waste_record.quantity) if waste_record.quantity else 0,
                    'unit': waste_record.stock_item.unit if waste_record.stock_item else '',
                    'cost_per_unit': float(waste_record.stock_item.cost_per_unit) if waste_record.stock_item else 0,
                    'total_cost': float(waste_record.total_cost) if waste_record.total_cost else 0,
                    'reason': waste_record.waste_reason.name,
                    'status': waste_record.status,
                    'requires_approval': waste_record.waste_reason.category.requires_approval
                }
            })
        else:
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManagerOrAdmin])
def run_waste_alerts(request):
    """
    Manually run waste alert checks
    """
    user = request.user

    # Run all alert checks
    daily_threshold = WasteAlertManager.check_daily_thresholds(
        branch_id=user.branch.id if user.branch else None
    )
    recurring_issues = WasteAlertManager.check_recurring_issues()
    pending_approvals = WasteAlertManager.check_pending_approvals()

    return Response({
        'success': True,
        'alerts_checked': True,
        'results': {
            'daily_threshold': daily_threshold,
            'recurring_issues': recurring_issues,
            'pending_approvals': pending_approvals
        },
        'total_alerts_created': (
            (1 if daily_threshold.get('threshold_exceeded', False) else 0) +
            recurring_issues.get('alerts_created', 0) +
            pending_approvals.get('alerts_created', 0)
        )
    })
