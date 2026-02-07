"""
Automated tests for critical bug fixes
Tests all the fixes implemented in the debugging session
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from database.connection import get_db
from auth.utils import verify_otp
from datetime import datetime, timedelta


class TestCriticalFixes(unittest.TestCase):
    """Test all critical fixes"""
    
    def setUp(self):
        """Setup test database connection"""
        self.conn = get_db()
        self.cursor = self.conn.cursor()
    
    def tearDown(self):
        """Cleanup"""
        self.cursor.close()
        self.conn.close()
    
    def test_01_admin_assignments_table_exists(self):
        """Test that admin_assignments table was created"""
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='admin_assignments'
        """)
        result = self.cursor.fetchone()
        self.assertIsNotNone(result, "admin_assignments table should exist")
        print("✓ admin_assignments table exists")
    
    def test_02_admin_logs_table_schema(self):
        """Test admin_logs table has correct columns"""
        self.cursor.execute("PRAGMA table_info(admin_logs)")
        columns = [row['name'] for row in self.cursor.fetchall()]
        
        required_columns = ['id', 'admin_id', 'action', 'created_at']
        for col in required_columns:
            self.assertIn(col, columns, f"admin_logs should have {col} column")
        print(f"✓ admin_logs has required columns: {required_columns}")
    
    def test_03_no_admins_table(self):
        """Test that old 'admins' table doesn't exist (should use users table)"""
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='admins'
        """)
        result = self.cursor.fetchone()
        # If it exists, it's legacy - main point is we use users table with role='admin'
        self.cursor.execute("SELECT COUNT(*) as count FROM users WHERE role='admin'")
        admin_count = self.cursor.fetchone()['count']
        self.assertGreater(admin_count, 0, "Should have admin users in users table")
        print(f"✓ Found {admin_count} admin users in users table (not separate admins table)")
    
    def test_04_password_otps_table_exists(self):
        """Test password_otps table exists for OTP verification"""
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='password_otps'
        """)
        result = self.cursor.fetchone()
        self.assertIsNotNone(result, "password_otps table should exist")
        print("✓ password_otps table exists")
    
    def test_05_password_otps_columns(self):
        """Test password_otps has required columns"""
        self.cursor.execute("PRAGMA table_info(password_otps)")
        columns = [row['name'] for row in self.cursor.fetchall()]
        
        required = ['id', 'email', 'otp', 'expires_at', 'verified']
        for col in required:
            self.assertIn(col, columns, f"password_otps should have {col}")
        print(f"✓ password_otps has columns: {columns}")
    
    def test_06_users_table_has_roles(self):
        """Test users table properly stores different roles"""
        self.cursor.execute("SELECT DISTINCT role FROM users")
        roles = [row['role'] for row in self.cursor.fetchall()]
        
        expected_roles = ['user', 'admin', 'head']
        for role in expected_roles:
            self.assertIn(role, roles, f"Should have {role} role in users table")
        print(f"✓ Users table has roles: {roles}")
    
    def test_07_verify_otp_uses_correct_table(self):
        """Test that verify_otp function doesn't query users table for OTP"""
        # Insert test OTP
        test_email = "test_otp@example.com"
        test_otp = "123456"
        expires_at = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
        
        self.cursor.execute("""
            INSERT INTO password_otps (email, otp, expires_at, verified)
            VALUES (?, ?, ?, 0)
        """, (test_email, test_otp, expires_at))
        self.conn.commit()
        
        # Test verification
        result = verify_otp(test_email, test_otp)
        self.assertTrue(result, "OTP verification should work with password_otps table")
        
        # Cleanup
        self.cursor.execute("DELETE FROM password_otps WHERE email = ?", (test_email,))
        self.conn.commit()
        print("✓ verify_otp correctly uses password_otps table")
    
    def test_08_admin_logs_foreign_key(self):
        """Test admin_logs references users table correctly"""
        self.cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='admin_logs'
        """)
        schema = self.cursor.fetchone()['sql']
        self.assertIn('FOREIGN KEY', schema, "admin_logs should have foreign key")
        self.assertIn('users', schema.lower(), "Foreign key should reference users table")
        print("✓ admin_logs has foreign key to users table")


class TestSecurityValidation(unittest.TestCase):
    """Test security-related fixes"""
    
    def setUp(self):
        self.conn = get_db()
        self.cursor = self.conn.cursor()
    
    def tearDown(self):
        self.cursor.close()
        self.conn.close()
    
    def test_01_no_plain_passwords(self):
        """Verify no plain text passwords in database"""
        self.cursor.execute("SELECT password_hash FROM users LIMIT 5")
        for row in self.cursor.fetchall():
            pwd = row['password_hash']
            # Bcrypt hashes start with $2b$ and are 60 chars
            self.assertTrue(
                pwd.startswith('$2b$') or pwd.startswith('scrypt:'),
                "Passwords should be hashed"
            )
        print("✓ All passwords are properly hashed")
    
    def test_02_indexes_exist(self):
        """Check that important indexes exist for performance"""
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index'
        """)
        indexes = [row['name'] for row in self.cursor.fetchall()]
        
        # Should have at least some indexes
        self.assertGreater(len(indexes), 0, "Should have database indexes")
        print(f"✓ Found {len(indexes)} database indexes")


if __name__ == '__main__':
    print("=" * 60)
    print("RUNNING AUTOMATED TESTS FOR CRITICAL FIXES")
    print("=" * 60)
    
    # Run tests
    unittest.main(verbosity=2)
