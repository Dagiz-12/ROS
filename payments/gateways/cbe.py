# payments/gateways/cbe.py
from .base import BasePaymentGateway
import requests
import json
from django.conf import settings


class CBEGateway(BasePaymentGateway):
    """CBE Payment Gateway Integration"""

    def __init__(self, config=None):
        super().__init__(config)
        self.api_key = self.config.get('api_key', '')
        self.merchant_id = self.config.get('merchant_id', '')
        self.callback_url = self.config.get('callback_url', '')

        # Set endpoints based on test mode
        if self.test_mode:
            self.base_url = "https://sandbox.cbe.com.et/api/v1"
        else:
            self.base_url = "https://api.cbe.com.et/api/v1"

    def initiate_payment(self, payment_data):
        """Initiate CBE payment"""
        endpoint = f"{self.base_url}/payment/initiate"

        payload = {
            'merchant_id': self.merchant_id,
            'api_key': self.api_key,
            'amount': float(payment_data['amount']),
            'currency': 'ETB',
            'customer_email': payment_data.get('customer_email', ''),
            'customer_phone': payment_data.get('customer_phone', ''),
            'description': payment_data.get('description', 'Restaurant Payment'),
            'order_id': str(payment_data['payment_id']),
            'callback_url': self.callback_url,
            'metadata': payment_data.get('metadata', {})
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'transaction_id': result.get('transaction_id'),
                    'payment_url': result.get('payment_url'),
                    'message': result.get('message', 'Payment initiated'),
                    'gateway_response': result
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'message': 'Failed to initiate payment'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Payment gateway error'
            }

    def verify_payment(self, transaction_id):
        """Verify CBE payment"""
        endpoint = f"{self.base_url}/payment/verify/{transaction_id}"

        payload = {
            'merchant_id': self.merchant_id,
            'api_key': self.api_key
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'status': result.get('status'),
                    'verified': result.get('verified', False),
                    'gateway_response': result
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'message': 'Failed to verify payment'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Payment verification error'
            }

    def refund_payment(self, transaction_id, amount):
        """Refund CBE payment"""
        endpoint = f"{self.base_url}/payment/refund"

        payload = {
            'merchant_id': self.merchant_id,
            'api_key': self.api_key,
            'transaction_id': transaction_id,
            'amount': float(amount),
            'reason': 'Customer request'
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'refund_id': result.get('refund_id'),
                    'message': result.get('message', 'Refund initiated'),
                    'gateway_response': result
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'message': 'Failed to process refund'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Refund processing error'
            }
