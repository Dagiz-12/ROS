# payments/urls.py - CORRECTED VERSION
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet, basename='payment')

urlpatterns = [
    # REST API routes from router
    path('', include(router.urls)),

    # ✅ CORRECTED CASHIER ENDPOINTS - USE THE RIGHT FUNCTION NAMES
    path('cashier/dashboard-data/', views.cashier_dashboard_data,
         name='cashier-dashboard-data'),
    path('cashier/process-payment/', views.cashier_process_payment,
         name='cashier-process-payment'),
    path('cashier/pending-orders/', views.cashier_pending_orders,
         name='cashier-pending-orders'),

    # ✅ LEGACY COMPATIBILITY ENDPOINTS (if needed)
    path('cashier-dashboard-data/', views.cashier_dashboard_data,
         name='legacy-cashier-dashboard'),

    # ✅ PAYMENT OPERATIONS (using ViewSet actions)
    # Note: These should be handled by the router above, but keeping for compatibility
    path('payments/<uuid:pk>/process/',
         views.PaymentViewSet.as_view({'post': 'process'}), name='payment-process'),
    path('payments/<uuid:pk>/verify/',
         views.PaymentViewSet.as_view({'post': 'verify_payment'}), name='payment-verify'),
    path('payments/<uuid:pk>/refund/',
         views.PaymentViewSet.as_view({'post': 'refund'}), name='payment-refund'),
    path('payments/<uuid:pk>/generate-receipt/',
         views.PaymentViewSet.as_view({'post': 'generate_detailed_receipt'}), name='payment-generate-receipt'),

    # ✅ RECEIPT PRINTING
    path('print-receipt/<uuid:payment_id>/',
         views.print_receipt, name='print-receipt'),
]
