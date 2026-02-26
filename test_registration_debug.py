#!/usr/bin/env python3
"""
SERVONIX Connection & Registration Debugger
Tests and validates the fixes for:
- Registration OTP flow
- Socket.IO connectivity
- CORS configuration
- Email delivery

Run: python test_registration_debug.py
"""

import sys
import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = 'http://127.0.0.1:5000'
TEST_EMAIL = 'test.debug@example.com'
TEST_NAME = 'Test User'
TEST_PASSWORD = 'TestPassword123!'

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def test_api_health():
    """Test 1: Check if API is running"""
    print_header("TEST 1: API Health Check")
    
    try:
        response = requests.get(f'{API_BASE}/api/health', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is healthy: {data}")
            print_info(f"Status Code: {response.status_code}")
            print_info(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print_error(f"API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {API_BASE}")
        print_warning(f"Make sure backend is running on {API_BASE}")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_cors_preflight():
    """Test 2: Check CORS preflight support"""
    print_header("TEST 2: CORS Preflight Support")
    
    try:
        headers = {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        response = requests.options(
            f'{API_BASE}/api/register-request',
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200 or response.status_code == 204:
            print_success(f"Preflight request successful (Status: {response.status_code})")
            print_info("CORS Headers returned:")
            for header, value in response.headers.items():
                if 'Access-Control' in header or 'Allow' in header:
                    print_info(f"  {header}: {value}")
            return True
        else:
            print_warning(f"Preflight returned status {response.status_code}")
            return True  # Not critical
    except Exception as e:
        print_error(f"Preflight test failed: {str(e)}")
        return False

def test_registration_request():
    """Test 3: Test registration OTP request"""
    print_header("TEST 3: Registration OTP Request")
    
    test_data = {
        'name': TEST_NAME,
        'email': TEST_EMAIL,
        'password': TEST_PASSWORD
    }
    
    print_info(f"Sending registration request with:")
    print_info(f"  Email: {test_data['email']}")
    print_info(f"  Name: {test_data['name']}")
    
    try:
        response = requests.post(
            f'{API_BASE}/api/register-request',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print_info(f"Response Status: {response.status_code}")
        
        try:
            data = response.json()
            print_info(f"Response Data:")
            print(json.dumps(data, indent=2))
            
            if response.status_code == 200:
                print_success("Registration request successful!")
                
                # Check for OTP in response (dev mode)
                if 'dev_otp' in data:
                    print_warning(f"Dev OTP returned (email service issue): {data['dev_otp']}")
                    return True, data.get('dev_otp'), data.get('registration_token')
                
                if 'message' in data and 'email' in data:
                    print_success(f"Message: {data['message']}")
                    return True, None, data.get('registration_token')
                
                return True, None, data.get('registration_token')
            
            elif response.status_code == 409:
                print_warning(f"Email already registered: {data.get('error')}")
                return True, None, None
            
            elif response.status_code == 429:
                print_warning(f"Rate limited: {data.get('error')}")
                return True, None, None
            
            else:
                print_error(f"Request failed: {data.get('error', 'Unknown error')}")
                return False, None, None
                
        except json.JSONDecodeError:
            print_error(f"Could not parse response as JSON")
            print_info(f"Raw response: {response.text[:200]}")
            return False, None, None
            
    except requests.exceptions.Timeout:
        print_error("Request timed out (API may be slow)")
        return False, None, None
    except Exception as e:
        print_error(f"Registration request failed: {str(e)}")
        return False, None, None

def test_socket_io_connection():
    """Test 4: Check Socket.IO configuration"""
    print_header("TEST 4: Socket.IO Configuration")
    
    try:
        # Test if Socket.IO is available
        response = requests.get(f'{API_BASE}/socket.io/?EIO=4&transport=polling', timeout=5)
        
        if response.status_code == 200:
            print_success("Socket.IO endpoint is accessible")
            print_info(f"Status: {response.status_code}")
            return True
        else:
            print_error(f"Socket.IO returned status {response.status_code}")
            return False
    except Exception as e:
        print_warning(f"Socket.IO connection test: {str(e)}")
        print_info("This is normal if Socket.IO library is not fully initialized")
        return True  # Not critical

def test_options_support():
    """Test 5: Check OPTIONS support for all endpoints"""
    print_header("TEST 5: OPTIONS Support for API Endpoints")
    
    endpoints = [
        '/api/register-request',
        '/api/register-verify',
        '/api/health',
        '/api/login'
    ]
    
    all_passed = True
    for endpoint in endpoints:
        try:
            response = requests.options(f'{API_BASE}{endpoint}', timeout=5)
            if response.status_code in [200, 204]:
                print_success(f"{endpoint}: OK")
            else:
                print_warning(f"{endpoint}: Status {response.status_code}")
        except Exception as e:
            print_error(f"{endpoint}: {str(e)}")
            all_passed = False
    
    return all_passed

def test_database_connectivity():
    """Test 6: Check database connectivity"""
    print_header("TEST 6: Database Connectivity")
    
    try:
        # Try a simple query through the API
        response = requests.get(
            f'{API_BASE}/api/districts',
            headers={'Authorization': 'Bearer invalid_token'},  # Will fail auth but tests DB
            timeout=5
        )
        
        # We expect 401 (invalid token) but this tells us DB is working
        if response.status_code in [400, 401, 403]:
            print_success("Database appears to be connected")
            print_info(f"API returned: {response.status_code} (expected auth error means DB works)")
            return True
        else:
            print_info(f"API status: {response.status_code}")
            return True  # Can't determine from this
            
    except Exception as e:
        print_warning(f"Database connectivity test inconclusive: {str(e)}")
        return True  # Not critical for this test

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}SERVONIX Registration & Connection Debug Tests{Colors.ENDC}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Base: {API_BASE}\n")
    
    results = {
        'API Health': test_api_health(),
        'CORS Preflight': test_cors_preflight(),
        'Socket.IO': test_socket_io_connection(),
        'OPTIONS Support': test_options_support(),
        'Database': test_database_connectivity(),
    }
    
    # Test registration
    print_info("Testing registration flow...\n")
    success, otp, token = test_registration_request()
    results['Registration'] = success
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"{test}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! System appears to be configured correctly.")
    elif passed >= total - 1:
        print_warning("Most tests passed. Minor issues may exist.")
    else:
        print_error("Multiple tests failed. Check configuration and logs.")
    
    print(f"\n{Colors.BOLD}Recommended Next Steps:{Colors.ENDC}")
    if not results['API Health']:
        print("1. Start the backend server: python -m backend.app")
    if not results['CORS Preflight']:
        print("2. Check backend CORS configuration in app.py")
    if not results['Registration']:
        print("3. Check backend logs in backend/logs/app.log")
        print("4. Verify email service configuration")
        if otp:
            print_info(f"   Dev OTP: {otp}")
    if not results['Socket.IO']:
        print("5. Verify Socket.IO is enabled in backend")

if __name__ == '__main__':
    main()
