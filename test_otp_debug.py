#!/usr/bin/env python
import sqlite3
import sys

db_paths = [
    'backend/data/bus_complaints.db',
    'bus_complaints.db',
    './bus_complaints.db'
]

for db_path in db_paths:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"Database found at: {db_path}")
        print("Tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check registration_otp table
        if any(t[0] == 'registration_otp' for t in tables):
            cursor.execute("SELECT * FROM registration_otp WHERE email = 'testuser@example.com'")
            row = cursor.fetchone()
            if row:
                print(f"\nOTP Record for testuser@example.com:")
                cursor.execute("PRAGMA table_info(registration_otp)")
                columns = [col[1] for col in cursor.fetchall()]
                for i, col in enumerate(columns):
                    print(f"  {col}: {row[i]}")
            else:
                print("\nNo OTP record found for testuser@example.com")
        
        conn.close()
        break
    except Exception as e:
        print(f"Error with {db_path}: {e}")
        continue

print("\nTesting OTP hash verification:")
import hashlib
import hmac

# Try manually - we need the OTP that was generated
# For testing, let's try common patterns
test_otps = ['123456', '000000', '999999']

for test_otp in test_otps:
    computed_hash = hashlib.sha256(test_otp.encode()).hexdigest()
    print(f"OTP {test_otp}: {computed_hash[:20]}...")
