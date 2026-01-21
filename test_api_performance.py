# test_api_performance.py
import requests
import time
import json
from datetime import datetime


def test_api_performance():
    BASE_URL = "http://localhost:8000"
    TEST_USER = "manager1"
    TEST_PASS = "manager123"

    print("=== API PERFORMANCE TESTING ===")

    # 1. Login to get token
    print("\n1. Testing Authentication...")
    start = time.time()
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login/",
        json={"username": TEST_USER, "password": TEST_PASS}
    )
    auth_time = time.time() - start

    if login_response.status_code == 200:
        token = login_response.json().get('access')
        print(f"✅ Login successful: {auth_time:.2f}s")
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test endpoints
    endpoints = [
        ("Profit Dashboard", "/profit-intelligence/api/dashboard/?view_level=restaurant"),
        ("Business Metrics", "/profit-intelligence/api/business-metrics/?period=today"),
        ("Menu Items", "/profit-intelligence/api/menu-items/?limit=5"),
        ("Sales Data", "/profit-intelligence/api/sales-data/?days=7"),
        ("Recent Activity", "/profit-intelligence/api/recent-activity/"),
    ]

    results = []

    for name, endpoint in endpoints:
        start = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        response_time = time.time() - start

        status = "✅" if response.status_code == 200 else "❌"
        results.append({
            "endpoint": name,
            "time": response_time,
            "status": status,
            "code": response.status_code,
            "size": len(response.content)
        })

        print(f"{status} {name}: {response_time:.2f}s ({len(response.content)} bytes)")

    # 3. Summary
    print("\n=== PERFORMANCE SUMMARY ===")
    avg_time = sum(r["time"] for r in results) / len(results)
    print(f"Average Response Time: {avg_time:.2f}s")
    print(f"Total API Calls: {len(results)}")

    # Check against targets
    slow_endpoints = [r for r in results if r["time"] > 0.5]
    if slow_endpoints:
        print("\n⚠️  SLOW ENDPOINTS (>0.5s):")
        for r in slow_endpoints:
            print(f"  {r['endpoint']}: {r['time']:.2f}s")

    return results


if __name__ == '__main__':
    test_api_performance()
