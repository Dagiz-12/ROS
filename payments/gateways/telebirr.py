# payments/gateways/telebirr.py
from .base import BasePaymentGateway
import requests
import hashlib
import time

import json


class TelebirrGateway(BasePaymentGateway):
    """Telebirr Payment Gateway Integration"""

    def __init__(self, config=None):
        super().__init__(config)
        self.app_id = self.config.get('app_id', '')
        self.app_key = self.config.get('app_key', '')

        # Set endpoints based on test mode
        if self.test_mode:
            self.base_url = "https://telebirr-sandbox.ethiotelecom.et/api/v1"
        else:
            self.base_url = "https://telebirr.ethiotelecom.et/api/v1"

    def _generate_signature(self, data):
        """Generate Telebirr signature"""
        import json
        import hmac
        import base64

        # Convert dict to sorted JSON string
        sorted_json = json.dumps(data, sort_keys=True)

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.app_key.encode('utf-8'),
            sorted_json.encode('utf-8'),
            hashlib.sha256
        ).digest()

        # Base64 encode
        return base64.b64encode(signature).decode('utf-8')

    def initiate_payment(self, payment_data):
        """Initiate Telebirr payment"""
        endpoint = f"{self.base_url}/payment/initiate"

        timestamp = str(int(time.time() * 1000))

        payload = {
            'appId': self.app_id,
            'nonce': timestamp,
            'timestamp': timestamp,
            'outTradeNo': str(payment_data['payment_id']),
            'subject': payment_data.get('description', 'Restaurant Payment'),
            'totalAmount': str(payment_data['amount']),
            'currency': 'ETB',
            'notifyUrl': self.config.get('notify_url', ''),
            'returnUrl': self.config.get('return_url', ''),
            'customerPhone': payment_data.get('customer_phone', ''),
            'attach': json.dumps(payment_data.get('metadata', {}))
        }

        # Generate signature
        payload['sign'] = self._generate_signature(payload)

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
                    'transaction_id': result.get('tradeNo'),
                    'payment_url': result.get('payUrl'),
                    'message': result.get('msg', 'Payment initiated'),
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
        """Verify Telebirr payment"""
        endpoint = f"{self.base_url}/payment/query"

        timestamp = str(int(time.time() * 1000))

        payload = {
            'appId': self.app_id,
            'nonce': timestamp,
            'timestamp': timestamp,
            'outTradeNo': transaction_id
        }

        # Generate signature
        payload['sign'] = self._generate_signature(payload)

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
                    'status': result.get('tradeStatus'),
                    'verified': result.get('tradeStatus') == 'SUCCESS',
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
        """Refund Telebirr payment"""
        endpoint = f"{self.base_url}/payment/refund"

        timestamp = str(int(time.time() * 1000))

        payload = {
            'appId': self.app_id,
            'nonce': timestamp,
            'timestamp': timestamp,
            'outTradeNo': transaction_id,
            'refundAmount': str(amount),
            'refundReason': 'Customer request'
        }

        # Generate signature
        payload['sign'] = self._generate_signature(payload)

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
                    'refund_id': result.get('refundNo'),
                    'message': result.get('msg', 'Refund initiated'),
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
