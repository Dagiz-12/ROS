# payments/gateways/base.py
import abc
from django.conf import settings


class BasePaymentGateway(abc.ABC):
    """Base class for all payment gateways"""

    def __init__(self, config=None):
        self.config = config or {}
        self.test_mode = self.config.get('test_mode', True)

    @abc.abstractmethod
    def initiate_payment(self, payment_data):
        """Initiate a payment"""
        pass

    @abc.abstractmethod
    def verify_payment(self, transaction_id):
        """Verify a payment"""
        pass

    @abc.abstractmethod
    def refund_payment(self, transaction_id, amount):
        """Refund a payment"""
        pass

    def get_gateway_name(self):
        """Get gateway name"""
        return self.__class__.__name__
