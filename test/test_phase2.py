import requests
import json
import time

BASE_URL = "http://localhost:8000/api"


def test_qr_system():
    print("=== Testing QR System ===")

    # 1. Login as admin to get tables
    login_data = {"username": "admin", "password": "admin123"}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    token = response.json().get('token')
    headers = {"Authorization": f"Bearer {token}"}

    print("1. Getting tables...")
    response = requests.get(f"{BASE_URL}/tables/tables/", headers=headers)
    tables = response.json()

    if tables:
        table_id = tables[0]['id']
        qr_token = tables[0]['qr_token']

        print(f"2. Validating QR token for table {table_id}...")
        qr_data = {"qr_token": qr_token, "table_id": table_id}
        response = requests.post(
            f"{BASE_URL}/tables/validate-qr/", json=qr_data)
        print(f"QR Validation: {response.json()}")

        return table_id, qr_token
    return None, None


def test_cart_system(table_id):
    print("\n=== Testing Cart System ===")

    # Create a session
    session_id = f"test_session_{int(time.time())}"

    print(f"1. Creating cart for session {session_id}...")
    response = requests.get(
        f"{BASE_URL}/tables/cart/?session_id={session_id}&table_id={table_id}")
    cart = response.json()
    print(f"Cart created: {cart}")

    # Get menu items
    # Assuming restaurant ID 1
    response = requests.get(f"{BASE_URL}/menu/public/1/")
    menu = response.json()

    if menu.get('categories'):
        first_category = menu['categories'][0]
        if first_category.get('items'):
            first_item = first_category['items'][0]
            item_id = first_item['id']

            print(f"2. Adding item {first_item['name']} to cart...")
            add_data = {
                "session_id": session_id,
                "table_id": table_id,
                "menu_item_id": item_id,
                "quantity": 2
            }
            response = requests.post(
                f"{BASE_URL}/tables/cart/add/", json=add_data)
            print(f"Added to cart: {response.json()}")

            # Get updated cart
            response = requests.get(
                f"{BASE_URL}/tables/cart/?session_id={session_id}&table_id={table_id}")
            updated_cart = response.json()
            print(f"Updated cart total: ${updated_cart['total_price']}")

            return session_id, cart['id']

    return None, None


def test_order_submission(session_id, table_id):
    print("\n=== Testing Order Submission ===")

    print("1. Submitting QR order...")
    order_data = {
        "session_id": session_id,
        "table_id": table_id,
        "customer_name": "Test Customer"
    }

    response = requests.post(
        f"{BASE_URL}/tables/submit-qr-order/", json=order_data)
    result = response.json()

    if response.status_code == 201:
        print(f"✅ Order submitted successfully!")
        print(f"Order Number: {result['order_number']}")
        print(f"Message: {result['message']}")
        return result['order']['id']
    else:
        print(f"❌ Order submission failed: {result}")
        return None


def test_order_management(order_id):
    print("\n=== Testing Order Management ===")

    # Login as waiter
    login_data = {"username": "waiter1", "password": "waiter123"}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    token = response.json().get('token')
    headers = {"Authorization": f"Bearer {token}"}

    print("1. Getting pending orders...")
    response = requests.get(
        f"{BASE_URL}/tables/orders/pending_confirmation/", headers=headers)
    pending_orders = response.json()
    print(f"Pending orders: {len(pending_orders.get('results', []))}")

    if order_id:
        print(f"2. Confirming order {order_id}...")
        status_data = {"status": "confirmed"}
        response = requests.post(
            f"{BASE_URL}/tables/orders/{order_id}/update_status/",
            json=status_data,
            headers=headers
        )
        print(f"Order confirmation: {response.status_code}")

        # Login as chef to see kitchen orders
        login_data = {"username": "chef1", "password": "chef123"}
        response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
        token = response.json().get('token')
        headers = {"Authorization": f"Bearer {token}"}

        print("3. Getting kitchen orders...")
        response = requests.get(
            f"{BASE_URL}/tables/orders/kitchen_orders/", headers=headers)
        kitchen_orders = response.json()
        print(f"Kitchen orders: {len(kitchen_orders)}")

        # Mark as preparing
        if order_id in [o['id'] for o in kitchen_orders]:
            print(f"4. Marking order as preparing...")
            status_data = {"status": "preparing"}
            response = requests.post(
                f"{BASE_URL}/tables/orders/{order_id}/update_status/",
                json=status_data,
                headers=headers
            )
            print(f"Order preparing: {response.status_code}")


def test_polling():
    print("\n=== Testing Polling System ===")

    # Login as chef
    login_data = {"username": "chef1", "password": "chef123"}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    token = response.json().get('token')
    headers = {"Authorization": f"Bearer {token}"}

    print("1. Getting polling updates...")
    response = requests.get(
        f"{BASE_URL}/core/polling/updates/?since=2024-01-01T00:00:00",
        headers=headers
    )
    updates = response.json()
    print(f"Polling response: {updates.keys()}")
    print(f"Next poll in: {updates.get('next_poll_in')} seconds")


if __name__ == "__main__":
    print("=== Phase 2 Testing ===\n")

    # Test QR system
    table_id, qr_token = test_qr_system()

    if table_id:
        # Test cart system
        session_id, cart_id = test_cart_system(table_id)

        if session_id:
            # Test order submission
            order_id = test_order_submission(session_id, table_id)

            if order_id:
                # Test order management
                test_order_management(order_id)

        # Test polling
        test_polling()

        print("\n✅ Phase 2 tests completed!")
    else:
        print("\n❌ Setup failed! Make sure to run migrations and create tables.")
