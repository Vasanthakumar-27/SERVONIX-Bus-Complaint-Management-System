"""Database connection and initialization"""
import sqlite3
import os
import time
from datetime import datetime

# Database file path - in project root /data directory (matching config.py)
# __file__ = backend/database/connection.py
# dirname(__file__) = backend/database
# dirname(dirname(__file__)) = backend
# dirname(dirname(dirname(__file__))) = project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'servonix.db')


def get_db():
    """Get database connection with improved settings"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
    # Enable WAL mode for better concurrent access
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')  # 30 seconds timeout
    return conn


def init_db():
    """Initialize database with schema - with retry logic"""
    max_retries = 5
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            conn = get_db()
            cursor = conn.cursor()
            break
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and attempt < max_retries - 1:
                print(f"Database locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      phone TEXT DEFAULT NULL,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'head')),
      token TEXT DEFAULT NULL,
      is_active BOOLEAN DEFAULT TRUE,
      last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
      reset_token TEXT DEFAULT NULL,
      reset_token_expires DATETIME DEFAULT NULL,
      otp TEXT DEFAULT NULL,
      otp_expiry DATETIME DEFAULT NULL,
      created_by INTEGER DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT NULL,
      profile_pic TEXT DEFAULT NULL,
      FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Create complaints table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS complaints (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      complaint_type TEXT NOT NULL,
      description TEXT NOT NULL,
      route_number TEXT DEFAULT NULL,
      bus_number TEXT DEFAULT NULL,
      from_location TEXT DEFAULT NULL,
      to_location TEXT DEFAULT NULL,
      incident_time DATETIME DEFAULT NULL,
      media_path TEXT DEFAULT NULL,
      status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in-progress', 'resolved', 'rejected')),
      assigned_to INTEGER DEFAULT NULL,
      admin_response TEXT DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT NULL,
      resolved_at DATETIME DEFAULT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Create feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      complaint_id INTEGER DEFAULT NULL,
      user_name TEXT DEFAULT NULL,
      user_email TEXT DEFAULT NULL,
      feedback_type TEXT DEFAULT 'general',
      message TEXT NOT NULL,
      rating INTEGER DEFAULT NULL CHECK (rating >= 1 AND rating <= 5),
      status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'responded')),
      admin_response TEXT DEFAULT NULL,
      reviewed_by INTEGER DEFAULT NULL,
      reviewed_at DATETIME DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
      FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Create messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sender_id INTEGER NOT NULL,
      receiver_id INTEGER NOT NULL,
      subject TEXT DEFAULT NULL,
      body TEXT NOT NULL,
      is_read BOOLEAN DEFAULT FALSE,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      read_at DATETIME DEFAULT NULL,
      FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Create complaint_messages table for communication on complaints
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS complaint_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      complaint_id INTEGER NOT NULL,
      sender_id INTEGER NOT NULL,
      message TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
      FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Create notifications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      type TEXT NOT NULL,
      title TEXT NOT NULL,
      message TEXT NOT NULL,
      related_id INTEGER DEFAULT NULL,
      is_read BOOLEAN DEFAULT FALSE,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      read_at DATETIME DEFAULT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Create feedback_chat table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback_chat (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      feedback_id INTEGER NOT NULL,
      sender_id INTEGER NOT NULL,
      message TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE,
      FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Create password_reset_otp table for secure password reset
    # OTP is stored as a hash for security
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS password_reset_otp (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL,
      otp_hash TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      expires_at DATETIME NOT NULL,
      used BOOLEAN DEFAULT FALSE,
      ip_address TEXT DEFAULT NULL
    )
    ''')
    
    # Create OTP rate limiting table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS otp_rate_limit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL,
      request_count INTEGER DEFAULT 1,
      window_start DATETIME DEFAULT CURRENT_TIMESTAMP,
      last_request DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create registration_otp table for secure registration verification
    # Stores pending registrations until OTP is verified
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registration_otp (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      otp_hash TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      expires_at DATETIME NOT NULL,
      ip_address TEXT DEFAULT NULL
    )
    ''')
    
    # Create admin_logs table for tracking admin actions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      admin_id INTEGER NOT NULL,
      action TEXT NOT NULL,
      details TEXT DEFAULT NULL,
      ip_address TEXT DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Create admin_assignments table for assigning routes to admins
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_assignments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      admin_id INTEGER NOT NULL,
      route_id INTEGER DEFAULT NULL,
      district_id INTEGER DEFAULT NULL,
      bus_id INTEGER DEFAULT NULL,
      priority INTEGER DEFAULT 1,
      assigned_by INTEGER DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # ============================================
    # District/Route/Bus Management Tables
    # ============================================
    
    # Create districts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS districts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      code TEXT NOT NULL UNIQUE,
      description TEXT DEFAULT NULL,
      is_active BOOLEAN DEFAULT TRUE,
      created_by INTEGER DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT NULL,
      FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Create routes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS routes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      route_number TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      district_id INTEGER DEFAULT NULL,
      start_point TEXT DEFAULT NULL,
      end_point TEXT DEFAULT NULL,
      description TEXT DEFAULT NULL,
      is_active BOOLEAN DEFAULT TRUE,
      created_by INTEGER DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT NULL,
      FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE SET NULL,
      FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Create buses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS buses (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      bus_number TEXT NOT NULL UNIQUE,
      route_id INTEGER DEFAULT NULL,
      bus_type TEXT DEFAULT 'regular' CHECK (bus_type IN ('regular', 'express', 'deluxe', 'ac')),
      capacity INTEGER DEFAULT 40,
      is_active BOOLEAN DEFAULT TRUE,
      created_by INTEGER DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT NULL,
      FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE SET NULL,
      FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Create admin_district_assignments table (assign admins to specific districts)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_district_assignments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      admin_id INTEGER NOT NULL,
      district_id INTEGER NOT NULL,
      is_primary BOOLEAN DEFAULT FALSE,
      assigned_by INTEGER DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(admin_id, district_id),
      FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE CASCADE,
      FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # ============================================
    # Indexes for new tables
    # ============================================
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_routes_district ON routes (district_id)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_buses_route ON buses (route_id)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_admin_district_admin ON admin_district_assignments (admin_id)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_admin_district_district ON admin_district_assignments (district_id)
    ''')
    
    # ============================================
    # Media Files Table for complaint attachments
    # ============================================
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media_files (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      mime_type TEXT DEFAULT NULL,
      file_size INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Create complaint_media junction table (links complaints to media files)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS complaint_media (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      complaint_id INTEGER NOT NULL,
      media_id INTEGER NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(complaint_id, media_id),
      FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
      FOREIGN KEY (media_id) REFERENCES media_files(id) ON DELETE CASCADE
    )
    ''')
    
    # Indexes for media tables
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_media_files_user ON media_files (user_id)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_complaint_media_complaint ON complaint_media (complaint_id)
    ''')

    # Create index for password_otps table
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_email_otp ON password_otps (email, otp)
    ''')
    
    # Create index for admin_logs table
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_logs (admin_id)
    ''')
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs (created_at)
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")


__all__ = ['get_db', 'init_db']
