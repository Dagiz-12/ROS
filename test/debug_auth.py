"""
Debug authentication token issue
"""

import requests
import json


def test_token_usage():
    print("Testing token usage...")

    # Login first
    login_data = {
        'username': 'waiter1',
        'password': 'waiter123'
    }

    response = requests.post(
        'http://localhost:8000/api/auth/login/', json=login_data)

    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get('access')
        print(f"✅ Got token: {token[:50]}...")

        # Try different header formats
        headers_formats = [
            ('Bearer', f'Bearer {token}'),
            ('Token', f'Token {token}'),
            ('JWT', f'JWT {token}'),
            ('Authorization', f'Bearer {token}'),
        ]

        for header_name, header_value in headers_formats:
            print(f"\nTrying: {header_name}: {header_value[:40]}...")

            headers = {header_name: header_value}
            response = requests.get(
                'http://localhost:8000/api/auth/profile/', headers=headers)

            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:100]}")

            if response.status_code == 200:
                print(f"✅ SUCCESS with format: {header_name}")
                break

    else:
        print(f"❌ Login failed: {response.status_code}")


# Run the debug
test_token_usage()
