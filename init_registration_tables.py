#!/usr/bin/env python
import sqlite3

db_path = 'data/servonix.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"Tables in {db_path}:")
for table in tables:
    print(f"  - {table[0]}")

# Check for registration_otp table
if any(t[0] == 'registration_otp' for t in tables):
    print("\n✓ registration_otp table EXISTS")
    cursor.execute("SELECT COUNT(*) FROM registration_otp")
    count = cursor.fetchone()[0]
    print(f"  Records: {count}")
else:
    print("\n✗ registration_otp table MISSING - THIS IS THE PROBLEM!")
    print("\nI need to create this table. Creating...")
    
    # Create the registration_otp table
    cursor.execute('''CREATE TABLE IF NOT EXISTS registration_otp (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      otp_hash TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      expires_at DATETIME NOT NULL,
      ip_address TEXT DEFAULT NULL
    )''')
    
    # Create otp_rate_limit table too if missing
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='otp_rate_limit'")
    if not cursor.fetchone():
        cursor.execute('''CREATE TABLE IF NOT EXISTS otp_rate_limit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT NOT NULL,
          request_count INTEGER DEFAULT 1,
          window_start DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_request DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
    
    conn.commit()
    print("✓ Tables created successfully!")

conn.close()
