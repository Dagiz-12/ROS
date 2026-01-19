# profit_intelligence/apps.py
from django.apps import AppConfig


class ProfitIntelligenceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profit_intelligence'
    verbose_name = 'Profit Intelligence'

    def ready(self):
        # Import signals
        import profit_intelligence.signals
