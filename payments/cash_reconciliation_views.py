# payments/cash_reconciliation_views.py - CORRECTED VERSION
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from django.db.models import Sum, Count, Q, F
from django.shortcuts import get_object_or_404

from .models import CashDrawerSession, ReconciliationRecord, DailyCashSummary, Payment
from .serializers import (
    CashDrawerSessionSerializer,
    ReconciliationRecordSerializer,
    DailyCashSummarySerializer,
    CashReconciliationDashboardSerializer
)
from accounts.permissions import IsCashierOrHigher, IsManagerOrAdmin


class CashDrawerViewSet(viewsets.ModelViewSet):
    """Manage cash drawer sessions"""
    queryset = CashDrawerSession.objects.all()
    serializer_class = CashDrawerSessionSerializer
    permission_classes = [IsAuthenticated, IsCashierOrHigher]

    def get_queryset(self):
        """Filter by user's branch"""
        user = self.request.user
        queryset = super().get_queryset()

        if user.role in ['admin', 'manager']:
            return queryset.filter(branch__restaurant=user.restaurant)
        else:
            return queryset.filter(cashier=user)

    @action(detail=False, methods=['post'])
    def start_session(self, request):
        """Start a new cash drawer session"""
        user = request.user

        # Check if user has an open session
        open_session = CashDrawerSession.objects.filter(
            cashier=user,
            status='open'
        ).first()

        if open_session:
            return Response({
                'error': 'You already have an open cash drawer session.',
                'session_id': str(open_session.session_id)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get starting cash from request
        starting_cash = Decimal(request.data.get('starting_cash', '0.00'))

        # Create new session
        session = CashDrawerSession.objects.create(
            cashier=user,
            branch=user.branch,
            starting_cash=starting_cash,
            expected_cash=starting_cash,  # Initially same as starting
            status='open'
        )

        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def close_session(self, request, pk=None):
        """Close a cash drawer session"""
        session = self.get_object()

        if session.status != 'open':
            return Response({
                'error': f'Session is already {session.status}.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get actual cash count from request
        actual_cash = Decimal(request.data.get('actual_cash', '0.00'))

        # Calculate totals before closing
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(
            hour=23, minute=59, second=59, microsecond=999999)

        # Get cash payments during session
        cash_payments = Payment.objects.filter(
            processed_by=session.cashier,
            payment_method='cash',
            created_at__range=[session.start_time, today_end],
            status='completed'
        ).aggregate(total_cash=Sum('amount'))['total_cash'] or Decimal('0.00')

        # Get digital payments (FIXED LINE 100)
        digital_payments = Payment.objects.filter(
            processed_by=session.cashier,
            payment_method__in=['cbe', 'telebirr', 'cbe_wallet', 'card'],
            created_at__range=[session.start_time, today_end],
            status='completed'
        ).aggregate(total_digital=Sum('amount'))['total_digital'] or Decimal('0.00')

        # Update session totals
        session.cash_sales = cash_payments
        session.digital_sales = digital_payments
        session.total_sales = cash_payments + digital_payments
        session.expected_cash = session.starting_cash + cash_payments

        # Close session
        reviewed_by = request.user if request.user.role in [
            'manager', 'admin'] else None
        session.close_session(actual_cash, reviewed_by)

        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current_session(self, request):
        """Get current user's open session"""
        user = request.user
        session = CashDrawerSession.objects.filter(
            cashier=user,
            status='open'
        ).first()

        if not session:
            return Response({'detail': 'No open session found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today_summary(self, request):
        """Get today's cash summary for the user's branch"""
        user = request.user
        today = timezone.now().date()  # FIXED: Defined 'today'

        # Get or create today's summary
        summary, created = DailyCashSummary.objects.get_or_create(
            date=today,
            branch=user.branch
        )

        # Update from today's payments if needed
        if created or not summary.is_reconciled:
            self._update_today_summary(summary, user.branch)

        serializer = DailyCashSummarySerializer(summary)
        return Response(serializer.data)

    def _update_today_summary(self, summary, branch):
        """Update summary from today's payments"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(
            hour=23, minute=59, second=59, microsecond=999999)

        # Get today's payments by method
        payments = Payment.objects.filter(
            order__table__branch=branch,
            created_at__range=[today_start, today_end],
            status='completed'
        ).values('payment_method').annotate(
            total=Sum('amount')
        )

        # Reset totals
        summary.cash_sales = Decimal('0.00')
        summary.cbe_sales = Decimal('0.00')
        summary.telebirr_sales = Decimal('0.00')
        summary.cbe_wallet_sales = Decimal('0.00')
        summary.card_sales = Decimal('0.00')

        # Update from payments
        for payment in payments:
            method = payment['payment_method']
            amount = payment['total'] or Decimal('0.00')

            if method == 'cash':
                summary.cash_sales = amount
            elif method == 'cbe':
                summary.cbe_sales = amount
            elif method == 'telebirr':
                summary.telebirr_sales = amount
            elif method == 'cbe_wallet':
                summary.cbe_wallet_sales = amount
            elif method == 'card':
                summary.card_sales = amount

        # Get cash drawer sessions for today (FIXED LINE 194)
        today_date = timezone.now().date()
        sessions = CashDrawerSession.objects.filter(
            branch=branch,
            start_time__date=today_date  # FIXED: Use today_date
        )

        summary.sessions_opened = sessions.count()
        summary.sessions_closed = sessions.filter(status='closed').count()
        summary.sessions_with_discrepancy = sessions.filter(
            status='closed',
            discrepancy__gt=Decimal('1.00')  # More than $1 discrepancy
        ).count()

        summary.calculate_totals()
        summary.save()


class ReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    """View reconciliation records"""
    queryset = ReconciliationRecord.objects.all()
    serializer_class = ReconciliationRecordSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        """Filter by user's restaurant"""
        user = self.request.user
        queryset = super().get_queryset()
        return queryset.filter(session__branch__restaurant=user.restaurant)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a reconciliation record"""
        record = self.get_object()

        if record.status == 'resolved':
            return Response({
                'error': 'This record is already resolved.'
            }, status=status.HTTP_400_BAD_REQUEST)

        resolution_notes = request.data.get('resolution_notes', '')

        record.resolution_notes = resolution_notes
        record.resolved_by = request.user
        record.resolved_at = timezone.now()
        record.status = 'resolved'
        record.save()

        # Also update the session if needed
        if record.session.status == 'under_review':
            record.session.status = 'closed'
            record.session.save()

        serializer = self.get_serializer(record)
        return Response(serializer.data)


class CashReconciliationDashboardViewSet(viewsets.ViewSet):
    """Dashboard data for cash reconciliation"""
    permission_classes = [IsAuthenticated, IsCashierOrHigher]

    @action(detail=False, methods=['get'])
    def dashboard_data(self, request):
        """Get comprehensive dashboard data"""
        user = request.user
        branch = user.branch

        # Today's data
        today = timezone.now().date()
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get today's summary
        summary, _ = DailyCashSummary.objects.get_or_create(
            date=today,
            branch=branch
        )

        # Get current open session
        current_session = CashDrawerSession.objects.filter(
            cashier=user,
            status='open'
        ).first()

        # Get today's payments
        today_payments = Payment.objects.filter(
            order__table__branch=branch,
            created_at__gte=today_start,
            status='completed'
        ).order_by('-created_at')[:10]

        # Get recent reconciliation issues
        recent_issues = ReconciliationRecord.objects.filter(
            session__branch=branch,
            status__in=['pending_review', 'disputed']
        ).order_by('-created_at')[:5]

        # Calculate metrics
        metrics = {
            'today_cash_sales': summary.cash_sales,
            'today_digital_sales': summary.total_sales - summary.cash_sales,
            'today_total_sales': summary.total_sales,
            'cash_discrepancy': summary.cash_discrepancy,
            'open_sessions': CashDrawerSession.objects.filter(
                branch=branch,
                status='open'
            ).count(),
            'pending_reconciliations': ReconciliationRecord.objects.filter(
                session__branch=branch,
                status='pending_review'
            ).count(),
        }

        data = {
            'metrics': metrics,
            'current_session': CashDrawerSessionSerializer(current_session).data if current_session else None,
            'today_summary': DailyCashSummarySerializer(summary).data,
            'recent_payments': self._serialize_payments(today_payments),
            'recent_issues': ReconciliationRecordSerializer(recent_issues, many=True).data,
        }

        return Response(data)

    def _serialize_payments(self, payments):
        """Helper to serialize payments"""
        return [{
            'id': p.id,
            'order_number': p.order.order_number if p.order else 'N/A',
            'amount': p.amount,
            'payment_method': p.get_payment_method_display(),
            'customer_name': p.customer_name or 'Guest',
            'processed_at': p.processed_at,
            'status': p.status
        } for p in payments]
