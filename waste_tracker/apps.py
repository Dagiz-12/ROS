# waste_tracker/apps.py
from django.apps import AppConfig


class WasteTrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'waste_tracker'

    def ready(self):
        # Import signals when app is ready
        import waste_tracker.signals
