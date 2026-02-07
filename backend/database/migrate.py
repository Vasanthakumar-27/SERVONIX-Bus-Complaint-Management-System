"""Database migration script to add new columns and tables"""
import sqlite3
import os
import sys

# Get the database path - same as connection.py
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'servonix.db')

def migrate():
    """Run all migrations"""
    print(f"Migrating database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Database does not exist. Run the app first to create it.")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    migrations = [
        # Add assigned_to column to complaints table if not exists
        ("ALTER TABLE complaints ADD COLUMN assigned_to INTEGER DEFAULT NULL", "complaints.assigned_to"),
        
        # Add title column to notifications table if not exists
        ("ALTER TABLE notifications ADD COLUMN title TEXT DEFAULT ''", "notifications.title"),
        
        # Add details column to admin_logs table if not exists
        ("ALTER TABLE admin_logs ADD COLUMN details TEXT DEFAULT NULL", "admin_logs.details"),
    ]
    
    # Check and add columns
    for sql, col_name in migrations:
        table, col = col_name.split('.')
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if col not in columns:
            try:
                cursor.execute(sql)
                print(f"✓ Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"✗ Error adding {col_name}: {e}")
        else:
            print(f"- Column already exists: {col_name}")
    
    # Create new tables if they don't exist
    new_tables = [
        # Districts table
        '''
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
        ''',
        
        # Routes table
        '''
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
        ''',
        
        # Buses table
        '''
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
        ''',
        
        # Admin-District assignments table
        '''
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
        ''',
    ]
    
    for table_sql in new_tables:
        try:
            cursor.execute(table_sql)
            # Extract table name from CREATE TABLE statement
            table_name = table_sql.split('CREATE TABLE IF NOT EXISTS ')[1].split('(')[0].strip()
            print(f"✓ Table ready: {table_name}")
        except sqlite3.OperationalError as e:
            print(f"✗ Error creating table: {e}")
    
    # Create indexes
    indexes = [
        ("CREATE INDEX IF NOT EXISTS idx_routes_district ON routes (district_id)", "idx_routes_district"),
        ("CREATE INDEX IF NOT EXISTS idx_buses_route ON buses (route_id)", "idx_buses_route"),
        ("CREATE INDEX IF NOT EXISTS idx_admin_district_admin ON admin_district_assignments (admin_id)", "idx_admin_district_admin"),
        ("CREATE INDEX IF NOT EXISTS idx_admin_district_district ON admin_district_assignments (district_id)", "idx_admin_district_district"),
        ("CREATE INDEX IF NOT EXISTS idx_complaints_assigned ON complaints (assigned_to)", "idx_complaints_assigned"),
    ]
    
    for idx_sql, idx_name in indexes:
        try:
            cursor.execute(idx_sql)
            print(f"✓ Index ready: {idx_name}")
        except sqlite3.OperationalError as e:
            print(f"✗ Error creating index {idx_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration complete!")
    return True


if __name__ == '__main__':
    migrate()
