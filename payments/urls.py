# payments/urls.py - FIXED VERSION
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import CashierPaymentAPI

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet, basename='payment')

urlpatterns = [
    # REST API routes from router
    path('', include(router.urls)),

    # ✅ INDUSTRY STANDARD CASHIER ENDPOINTS
    path('cashier/dashboard-data/', views.cashier_dashboard,
         name='cashier-dashboard-data'),
    path('cashier/process-payment/', views.cashier_process_payment,
         name='cashier-process-payment'),
    path('cashier/pending-orders/', views.cashier_pending_orders,
         name='cashier-pending-orders'),

    # ✅ Use ViewSet actions for payment operations (these exist in PaymentViewSet)
    path('<uuid:payment_id>/process/',
         views.PaymentViewSet.as_view({'post': 'process'}), name='payment-process'),
    path('<uuid:payment_id>/verify/',
         views.PaymentViewSet.as_view({'post': 'verify_payment'}), name='payment-verify'),
    path('<uuid:payment_id>/refund/',
         views.PaymentViewSet.as_view({'post': 'refund'}), name='payment-refund'),
    path('<uuid:payment_id>/receipt/', views.PaymentViewSet.as_view(
        {'post': 'generate_detailed_receipt'}), name='payment-receipt'),

    # ✅ Legacy endpoint for receipt printing (uses existing print_receipt function)
    path('print-receipt/<uuid:payment_id>/',
         views.print_receipt, name='print-receipt'),
]
