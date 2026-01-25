# payments/apps.py - COMPLETE FILE
from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'

    def ready(self):
        # Import and connect signals
        try:
            import payments.signals
            print("✅ Payment signals loaded successfully")
        except Exception as e:
            print(f"⚠️ Failed to load payment signals: {e}")
