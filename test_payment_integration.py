# test_payment_integration.py
import requests
import json

BASE_URL = "http://localhost:8000"


def test_cashier_dashboard():
    """Test cashier dashboard endpoint"""
    response = requests.get(f"{BASE_URL}/api/payments/cashier/dashboard-data/")
    print(f"Dashboard Status: {response.status_code}")
    print(f"Dashboard Response: {response.json()}")
    return response.ok


def test_payment_processing():
    """Test payment processing"""
    # First, get an order that needs payment
    dashboard_response = requests.get(
        f"{BASE_URL}/api/payments/cashier/dashboard-data/")
    dashboard_data = dashboard_response.json()

    if dashboard_data.get('pending_orders', {}).get('orders'):
        order = dashboard_data['pending_orders']['orders'][0]
        order_id = order['id']

        # Process payment
        payment_data = {
            "order_id": order_id,
            "payment_method": "cash",
            "amount": float(order['total_amount']),
            "cash_received": float(order['total_amount']) + 10.00,
            "customer_name": order.get('customer_name', 'Test Customer')
        }

        response = requests.post(
            f"{BASE_URL}/api/payments/cashier/process-payment/",
            json=payment_data,
            headers={"Content-Type": "application/json"}
        )

        print(f"Payment Status: {response.status_code}")
        print(f"Payment Response: {response.json()}")
        return response.ok
    else:
        print("No pending orders found")
        return False


if __name__ == "__main__":
    print("Testing Cashier Dashboard...")
    test_cashier_dashboard()

    print("\nTesting Payment Processing...")
    test_payment_processing()
