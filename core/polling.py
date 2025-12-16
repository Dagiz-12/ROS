import time
from django.utils import timezone
from django.core.cache import cache


class SmartPoller:
    """Smart adaptive polling system"""

    def __init__(self, role, base_interval):
        self.role = role
        self.base_interval = base_interval
        self.current_interval = base_interval
        self.is_active = False
        self.last_activity = timezone.now()
        self.activity_count = 0

        # Configuration
        self.config = {
            'MIN_INTERVAL': 5,  # seconds
            'MAX_INTERVAL': 60,  # seconds
            'ACTIVITY_WINDOW': 60,  # seconds to consider for activity
            'PEAK_HOURS': [11, 12, 13, 18, 19, 20],  # 11AM-2PM, 6PM-9PM
        }

    def start(self):
        """Start polling"""
        self.is_active = True
        self.last_activity = timezone.now()

    def stop(self):
        """Stop polling"""
        self.is_active = False

    def record_activity(self):
        """Record that activity happened"""
        self.activity_count += 1
        self.last_activity = timezone.now()

        # Store in cache for cross-request tracking
        cache_key = f'polling_activity_{self.role}'
        current_activity = cache.get(cache_key, 0)
        cache.set(cache_key, current_activity + 1, timeout=60)

    def adjust_interval(self, has_activity=False, is_peak_hours=False):
        """Adaptively adjust polling interval"""
        current_hour = timezone.now().hour
        is_peak = current_hour in self.config['PEAK_HOURS']

        # Get activity from cache (cross-request)
        cache_key = f'polling_activity_{self.role}'
        recent_activity = cache.get(cache_key, 0)

        # Adjust based on multiple factors
        if recent_activity > 5 or has_activity:
            # High activity: poll faster
            self.current_interval = max(
                self.config['MIN_INTERVAL'],
                self.base_interval / 2
            )
        elif is_peak or is_peak_hours:
            # Peak hours: moderate polling
            self.current_interval = max(
                self.config['MIN_INTERVAL'] * 2,
                self.base_interval * 0.75
            )
        elif recent_activity == 0:
            # No activity: poll slower
            self.current_interval = min(
                self.config['MAX_INTERVAL'],
                self.current_interval * 1.5
            )
        else:
            # Normal conditions
            self.current_interval = self.base_interval

        # Ensure within bounds
        self.current_interval = max(
            self.config['MIN_INTERVAL'],
            min(self.config['MAX_INTERVAL'], self.current_interval)
        )

        return self.current_interval

    def should_poll(self):
        """Determine if it's time to poll"""
        if not self.is_active:
            return False

        time_since_last = (timezone.now() - self.last_activity).total_seconds()
        return time_since_last >= self.current_interval

    def get_next_poll_time(self):
        """Get when next poll should happen"""
        if not self.is_active:
            return None

        return self.last_activity + timezone.timedelta(seconds=self.current_interval)


# Global polling configuration
POLLING_CONFIG = {
    'DEFAULT_INTERVAL': 20,  # seconds
    'ROLE_INTERVALS': {
        'CHEF': 15,      # Fast updates for kitchen efficiency
        'WAITER': 20,    # Balance between real-time and battery
        'MANAGER': 30,   # Analytics don't need real-time
        'CASHIER': 20,   # Payment status updates
        'ADMIN': 30,     # System monitoring
    },
    'ADAPTIVE_POLLING': True,
    'LONG_POLLING_TIMEOUT': 10,
    'MAX_POLLING_INTERVAL': 60,  # During errors or idle
    'MIN_POLLING_INTERVAL': 5,   # When very active
}
