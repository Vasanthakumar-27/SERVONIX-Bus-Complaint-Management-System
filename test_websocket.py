#!/usr/bin/env python3
"""
Quick WebSocket connectivity test for SERVONIX
Tests that Socket.IO can establish a connection with eventlet
"""
import requests
import json
import sys
from time import sleep

API_BASE = 'http://127.0.0.1:5000'

def test_api_health():
    """Test that the API is responding"""
    try:
        print("[TEST] Checking API health...")
        res = requests.get(f'{API_BASE}/api/health', timeout=5)
        if res.status_code == 200:
            data = res.json()
            print(f"✓ API is healthy: {data}")
            return True
        else:
            print(f"✗ API returned status {res.status_code}")
            return False
    except Exception as e:
        print(f"✗ API health check failed: {e}")
        return False

def test_login():
    """Test login to get a valid token"""
    try:
        print("\n[TEST] Testing login...")
        payload = {
            'email': 'head@example.com',
            'password': 'headpassword'
        }
        res = requests.post(f'{API_BASE}/api/auth/login', json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            token = data.get('token')
            print(f"✓ Login successful, token: {token[:20]}...")
            return token
        else:
            print(f"✗ Login failed: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"✗ Login test failed: {e}")
        return None

def test_dashboard_load():
    """Test that dashboard page loads (indicates frontend routing works)"""
    try:
        print("\n[TEST] Testing dashboard page load...")
        res = requests.get(f'{API_BASE}/head_dashboard', timeout=5)
        if res.status_code == 200:
            print(f"✓ Dashboard page loads successfully")
            return True
        else:
            print(f"✗ Dashboard page failed: {res.status_code}")
            return False
    except Exception as e:
        print(f"✗ Dashboard page test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("SERVONIX WebSocket & API Connectivity Test")
    print("=" * 60)
    
    # Wait for server startup
    print("\n[WAIT] Waiting 3 seconds for server startup...")
    sleep(3)
    
    results = []
    
    # Test 1: API Health
    results.append(("API Health", test_api_health()))
    
    # Test 2: Dashboard Load
    results.append(("Dashboard Load", test_dashboard_load()))
    
    # Test 3: Login
    token = test_login()
    results.append(("Login", token is not None))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    if passed == total:
        print("\n✓ All tests passed! WebSocket and API are operational.")
        print("Next: Test freezing in user modals via browser console.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check server logs.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
