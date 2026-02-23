"""
Database connection and initialization.

Strategy:
  - DATABASE_URL env var set  →  PostgreSQL  (Render persistent DB)
  - DATABASE_URL not set      →  SQLite      (local dev, unchanged)

A thin compatibility layer (_PgCursor / _PgConn) makes the PostgreSQL
connection behave exactly like a sqlite3 connection so every route file
works without a single change:
  • ? placeholders  →  %s
  • datetime('now') →  NOW()
  • INSERT OR IGNORE →  INSERT … ON CONFLICT DO NOTHING
  • cursor.lastrowid populated via RETURNING id
  • rows support both dict-key access (row['name']) and int-index (row[0])
"""
import re
import sqlite3
import os
import time
from datetime import datetime
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

# SQLite fallback path (local dev only)
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data', 'servonix.db'
)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# ---------------------------------------------------------------------------
# Unified Row  (works with both SQLite and PostgreSQL results)
# ---------------------------------------------------------------------------
class _Row:
    """Behaves like sqlite3.Row: supports row['col'] AND row[0] AND row.get()."""
    __slots__ = ('_data', '_keys')

    def __init__(self, columns, values):
        self._keys = list(columns)
        self._data = dict(zip(columns, values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._data[self._keys[key]]
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._keys

    def __iter__(self):
        return iter(self._keys)

    def __contains__(self, key):
        return key in self._data

    def __repr__(self):
        return repr(self._data)


# ---------------------------------------------------------------------------
# PostgreSQL cursor wrapper
# ---------------------------------------------------------------------------
class _PgCursor:
    """
    Wraps a raw psycopg2 cursor and provides a sqlite3-compatible interface.
    All SQL written with ? placeholders and sqlite-isms works transparently.
    """

    def __init__(self, raw_cursor):
        self._c = raw_cursor
        self.lastrowid = None

    # -- translation ---------------------------------------------------------
    @staticmethod
    def _translate(sql):
        """
        Translate SQLite SQL dialect → PostgreSQL SQL dialect.
        Returns (translated_sql, was_insert_or_ignore).
        """
        was_or_ignore = bool(re.search(r'INSERT\s+OR\s+IGNORE', sql, re.IGNORECASE))
        sql = sql.replace('?', '%s')
        sql = re.sub(r"datetime\s*\(\s*'now'\s*\)", 'NOW()', sql, flags=re.IGNORECASE)
        sql = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', sql, flags=re.IGNORECASE)
        return sql, was_or_ignore

    # -- execute -------------------------------------------------------------
    def execute(self, sql, params=None):
        sql, was_or_ignore = self._translate(sql)
        is_insert = sql.strip().upper().startswith('INSERT')

        if is_insert and 'RETURNING' not in sql.upper():
            suffix = ' ON CONFLICT DO NOTHING RETURNING id' if was_or_ignore \
                     else ' RETURNING id'
            sql = sql.rstrip('; \n') + suffix

        if params is not None:
            self._c.execute(sql, list(params) if not isinstance(params, (list, tuple)) else params)
        else:
            self._c.execute(sql)

        if is_insert:
            try:
                row = self._c.fetchone()
                self.lastrowid = row[0] if row else None
            except Exception:
                self.lastrowid = None

        return self

    def executemany(self, sql, params_list):
        sql, _ = self._translate(sql)
        self._c.executemany(sql, params_list)

    # -- result helpers ------------------------------------------------------
    def _wrap(self, raw_row):
        if raw_row is None:
            return None
        cols = [d[0] for d in self._c.description] if self._c.description else []
        return _Row(cols, raw_row)

    def fetchone(self):
        return self._wrap(self._c.fetchone())

    def fetchall(self):
        if not self._c.description:
            return []
        cols = [d[0] for d in self._c.description]
        return [_Row(cols, r) for r in self._c.fetchall()]

    def close(self):
        try:
            self._c.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# PostgreSQL connection wrapper
# ---------------------------------------------------------------------------
class _PgConn:
    """Wraps a psycopg2 connection to be drop-in compatible with sqlite3."""

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return _PgCursor(self._conn.cursor())

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()




# ---------------------------------------------------------------------------
# get_db  – the one function every route calls
# ---------------------------------------------------------------------------
def get_db():
    """Return a database connection (PostgreSQL or SQLite depending on env)."""
    if DATABASE_URL:
        import psycopg2
        url = DATABASE_URL
        # Render issues postgres:// but psycopg2 requires postgresql://
        if url.startswith('postgres://'):
            url = 'postgresql://' + url[len('postgres://'):]
        raw = psycopg2.connect(url)
        raw.autocommit = False
        return _PgConn(raw)

    # Local dev – SQLite (unchanged behaviour)
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn



# ---------------------------------------------------------------------------
# SQLite DDL  (local dev – original schema, all columns included from start)
# ---------------------------------------------------------------------------
def _create_tables_sqlite(cursor):
    stmts = [
        '''CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          phone TEXT DEFAULT NULL,
          password_hash TEXT NOT NULL,
          role TEXT DEFAULT 'user' CHECK (role IN ('user','admin','head')),
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
        )''',
        '''CREATE TABLE IF NOT EXISTS complaints (
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
          status TEXT DEFAULT 'pending'
            CHECK (status IN ('pending','in-progress','resolved','rejected')),
          assigned_to INTEGER DEFAULT NULL,
          admin_response TEXT DEFAULT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT NULL,
          resolved_at DATETIME DEFAULT NULL,
          name TEXT DEFAULT NULL,
          email TEXT DEFAULT NULL,
          category TEXT DEFAULT NULL,
          route TEXT DEFAULT NULL,
          district_id INTEGER DEFAULT NULL,
          proof_path TEXT DEFAULT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          complaint_id INTEGER DEFAULT NULL,
          user_name TEXT DEFAULT NULL,
          user_email TEXT DEFAULT NULL,
          feedback_type TEXT DEFAULT 'general',
          message TEXT NOT NULL,
          rating INTEGER DEFAULT NULL CHECK (rating >= 1 AND rating <= 5),
          status TEXT DEFAULT 'pending'
            CHECK (status IN ('pending','reviewed','responded')),
          admin_response TEXT DEFAULT NULL,
          reviewed_by INTEGER DEFAULT NULL,
          reviewed_at DATETIME DEFAULT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
          FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS messages (
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
        )''',
        '''CREATE TABLE IF NOT EXISTS complaint_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          complaint_id INTEGER NOT NULL,
          sender_id INTEGER NOT NULL,
          message TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
          FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS notifications (
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
        )''',
        '''CREATE TABLE IF NOT EXISTS feedback_chat (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          feedback_id INTEGER NOT NULL,
          sender_id INTEGER NOT NULL,
          message TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE,
          FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS password_reset_otp (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT NOT NULL,
          otp_hash TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          expires_at DATETIME NOT NULL,
          used BOOLEAN DEFAULT FALSE,
          ip_address TEXT DEFAULT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS otp_rate_limit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT NOT NULL,
          request_count INTEGER DEFAULT 1,
          window_start DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_request DATETIME DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS registration_otp (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          otp_hash TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          expires_at DATETIME NOT NULL,
          ip_address TEXT DEFAULT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS admin_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          admin_id INTEGER NOT NULL,
          admin_name TEXT DEFAULT NULL,
          action TEXT NOT NULL,
          details TEXT DEFAULT NULL,
          ip_address TEXT DEFAULT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS admin_assignments (
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
        )''',
        '''CREATE TABLE IF NOT EXISTS districts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          code TEXT NOT NULL UNIQUE,
          description TEXT DEFAULT NULL,
          is_active BOOLEAN DEFAULT TRUE,
          created_by INTEGER DEFAULT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS routes (
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
        )''',
        '''CREATE TABLE IF NOT EXISTS buses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          bus_number TEXT NOT NULL UNIQUE,
          route_id INTEGER DEFAULT NULL,
          bus_type TEXT DEFAULT 'regular'
            CHECK (bus_type IN ('regular','express','deluxe','ac')),
          capacity INTEGER DEFAULT 40,
          is_active BOOLEAN DEFAULT TRUE,
          created_by INTEGER DEFAULT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT NULL,
          FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE SET NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS admin_district_assignments (
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
        )''',
        '''CREATE TABLE IF NOT EXISTS media_files (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          file_name TEXT NOT NULL,
          file_path TEXT NOT NULL,
          mime_type TEXT DEFAULT NULL,
          file_size INTEGER DEFAULT 0,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS complaint_media (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          complaint_id INTEGER NOT NULL,
          media_id INTEGER NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(complaint_id, media_id),
          FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
          FOREIGN KEY (media_id) REFERENCES media_files(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS password_otps (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT NOT NULL,
          otp TEXT NOT NULL,
          expires_at DATETIME NOT NULL,
          verified INTEGER DEFAULT 0,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS user_notifications (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          type TEXT NOT NULL DEFAULT 'info',
          message TEXT NOT NULL,
          related_id INTEGER DEFAULT NULL,
          is_read BOOLEAN DEFAULT FALSE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        # Idempotent ALTER TABLE migrations for pre-existing SQLite DBs
        # (silently ignored if column already exists)
    ]
    for sql in stmts:
        cursor.execute(sql)

    # Idempotent migrations for existing SQLite databases
    _silent_alters = [
        'ALTER TABLE complaints ADD COLUMN name TEXT DEFAULT NULL',
        'ALTER TABLE complaints ADD COLUMN email TEXT DEFAULT NULL',
        'ALTER TABLE complaints ADD COLUMN category TEXT DEFAULT NULL',
        'ALTER TABLE complaints ADD COLUMN route TEXT DEFAULT NULL',
        'ALTER TABLE complaints ADD COLUMN district_id INTEGER DEFAULT NULL',
        'ALTER TABLE complaints ADD COLUMN proof_path TEXT DEFAULT NULL',
        'ALTER TABLE admin_assignments ADD COLUMN district_id INTEGER DEFAULT NULL',
        'ALTER TABLE admin_assignments ADD COLUMN bus_id INTEGER DEFAULT NULL',
        'ALTER TABLE admin_assignments ADD COLUMN priority INTEGER DEFAULT 1',
        'ALTER TABLE admin_assignments ADD COLUMN assigned_by INTEGER DEFAULT NULL',
        'ALTER TABLE admin_logs ADD COLUMN admin_name TEXT DEFAULT NULL',
    ]
    for sql in _silent_alters:
        try:
            cursor.execute(sql)
        except Exception:
            pass

    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_routes_district ON routes (district_id)',
        'CREATE INDEX IF NOT EXISTS idx_buses_route ON buses (route_id)',
        'CREATE INDEX IF NOT EXISTS idx_admin_district_admin ON admin_district_assignments (admin_id)',
        'CREATE INDEX IF NOT EXISTS idx_admin_district_district ON admin_district_assignments (district_id)',
        'CREATE INDEX IF NOT EXISTS idx_media_files_user ON media_files (user_id)',
        'CREATE INDEX IF NOT EXISTS idx_complaint_media_complaint ON complaint_media (complaint_id)',
        'CREATE INDEX IF NOT EXISTS idx_email_otp ON password_otps (email, otp)',
        'CREATE INDEX IF NOT EXISTS idx_user_notif_user_id ON user_notifications (user_id, is_read)',
        'CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_logs (admin_id)',
        'CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs (created_at)',
    ]
    for sql in indexes:
        cursor.execute(sql)


# ---------------------------------------------------------------------------
# PostgreSQL DDL  (SERIAL, BOOLEAN, TIMESTAMP — no ALTERs needed)
# ---------------------------------------------------------------------------
def _create_tables_postgres(raw_pg_cursor):
    """Run PostgreSQL DDL directly on the raw psycopg2 cursor (bypasses wrapper)."""
    stmts = [
        '''CREATE TABLE IF NOT EXISTS users (
          id SERIAL PRIMARY KEY,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          phone TEXT DEFAULT NULL,
          password_hash TEXT NOT NULL,
          role TEXT DEFAULT 'user' CHECK (role IN ('user','admin','head')),
          token TEXT DEFAULT NULL,
          is_active BOOLEAN DEFAULT TRUE,
          last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          reset_token TEXT DEFAULT NULL,
          reset_token_expires TIMESTAMP DEFAULT NULL,
          otp TEXT DEFAULT NULL,
          otp_expiry TIMESTAMP DEFAULT NULL,
          created_by INTEGER DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT NULL,
          profile_pic TEXT DEFAULT NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS complaints (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          complaint_type TEXT NOT NULL,
          description TEXT NOT NULL,
          route_number TEXT DEFAULT NULL,
          bus_number TEXT DEFAULT NULL,
          from_location TEXT DEFAULT NULL,
          to_location TEXT DEFAULT NULL,
          incident_time TIMESTAMP DEFAULT NULL,
          media_path TEXT DEFAULT NULL,
          status TEXT DEFAULT 'pending'
            CHECK (status IN ('pending','in-progress','resolved','rejected')),
          assigned_to INTEGER DEFAULT NULL,
          admin_response TEXT DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT NULL,
          resolved_at TIMESTAMP DEFAULT NULL,
          name TEXT DEFAULT NULL,
          email TEXT DEFAULT NULL,
          category TEXT DEFAULT NULL,
          route TEXT DEFAULT NULL,
          district_id INTEGER DEFAULT NULL,
          proof_path TEXT DEFAULT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS feedback (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          complaint_id INTEGER DEFAULT NULL,
          user_name TEXT DEFAULT NULL,
          user_email TEXT DEFAULT NULL,
          feedback_type TEXT DEFAULT 'general',
          message TEXT NOT NULL,
          rating INTEGER DEFAULT NULL CHECK (rating >= 1 AND rating <= 5),
          status TEXT DEFAULT 'pending'
            CHECK (status IN ('pending','reviewed','responded')),
          admin_response TEXT DEFAULT NULL,
          reviewed_by INTEGER DEFAULT NULL,
          reviewed_at TIMESTAMP DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
          FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS messages (
          id SERIAL PRIMARY KEY,
          sender_id INTEGER NOT NULL,
          receiver_id INTEGER NOT NULL,
          subject TEXT DEFAULT NULL,
          body TEXT NOT NULL,
          is_read BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          read_at TIMESTAMP DEFAULT NULL,
          FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS complaint_messages (
          id SERIAL PRIMARY KEY,
          complaint_id INTEGER NOT NULL,
          sender_id INTEGER NOT NULL,
          message TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
          FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS notifications (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          type TEXT NOT NULL,
          title TEXT NOT NULL,
          message TEXT NOT NULL,
          related_id INTEGER DEFAULT NULL,
          is_read BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          read_at TIMESTAMP DEFAULT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS feedback_chat (
          id SERIAL PRIMARY KEY,
          feedback_id INTEGER NOT NULL,
          sender_id INTEGER NOT NULL,
          message TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE,
          FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS password_reset_otp (
          id SERIAL PRIMARY KEY,
          email TEXT NOT NULL,
          otp_hash TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          expires_at TIMESTAMP NOT NULL,
          used BOOLEAN DEFAULT FALSE,
          ip_address TEXT DEFAULT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS otp_rate_limit (
          id SERIAL PRIMARY KEY,
          email TEXT NOT NULL,
          request_count INTEGER DEFAULT 1,
          window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          last_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS registration_otp (
          id SERIAL PRIMARY KEY,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          otp_hash TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          expires_at TIMESTAMP NOT NULL,
          ip_address TEXT DEFAULT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS admin_logs (
          id SERIAL PRIMARY KEY,
          admin_id INTEGER NOT NULL,
          admin_name TEXT DEFAULT NULL,
          action TEXT NOT NULL,
          details TEXT DEFAULT NULL,
          ip_address TEXT DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS admin_assignments (
          id SERIAL PRIMARY KEY,
          admin_id INTEGER NOT NULL,
          route_id INTEGER DEFAULT NULL,
          district_id INTEGER DEFAULT NULL,
          bus_id INTEGER DEFAULT NULL,
          priority INTEGER DEFAULT 1,
          assigned_by INTEGER DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS districts (
          id SERIAL PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          code TEXT NOT NULL UNIQUE,
          description TEXT DEFAULT NULL,
          is_active BOOLEAN DEFAULT TRUE,
          created_by INTEGER DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS routes (
          id SERIAL PRIMARY KEY,
          route_number TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL,
          district_id INTEGER DEFAULT NULL,
          start_point TEXT DEFAULT NULL,
          end_point TEXT DEFAULT NULL,
          description TEXT DEFAULT NULL,
          is_active BOOLEAN DEFAULT TRUE,
          created_by INTEGER DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT NULL,
          FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE SET NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS buses (
          id SERIAL PRIMARY KEY,
          bus_number TEXT NOT NULL UNIQUE,
          route_id INTEGER DEFAULT NULL,
          bus_type TEXT DEFAULT 'regular'
            CHECK (bus_type IN ('regular','express','deluxe','ac')),
          capacity INTEGER DEFAULT 40,
          is_active BOOLEAN DEFAULT TRUE,
          created_by INTEGER DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT NULL,
          FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE SET NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS admin_district_assignments (
          id SERIAL PRIMARY KEY,
          admin_id INTEGER NOT NULL,
          district_id INTEGER NOT NULL,
          is_primary BOOLEAN DEFAULT FALSE,
          assigned_by INTEGER DEFAULT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(admin_id, district_id),
          FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE CASCADE,
          FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS media_files (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          file_name TEXT NOT NULL,
          file_path TEXT NOT NULL,
          mime_type TEXT DEFAULT NULL,
          file_size INTEGER DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS complaint_media (
          id SERIAL PRIMARY KEY,
          complaint_id INTEGER NOT NULL,
          media_id INTEGER NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(complaint_id, media_id),
          FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
          FOREIGN KEY (media_id) REFERENCES media_files(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS password_otps (
          id SERIAL PRIMARY KEY,
          email TEXT NOT NULL,
          otp TEXT NOT NULL,
          expires_at TIMESTAMP NOT NULL,
          verified INTEGER DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS user_notifications (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          type TEXT NOT NULL DEFAULT 'info',
          message TEXT NOT NULL,
          related_id INTEGER DEFAULT NULL,
          is_read BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )''',
        'CREATE INDEX IF NOT EXISTS idx_routes_district ON routes (district_id)',
        'CREATE INDEX IF NOT EXISTS idx_buses_route ON buses (route_id)',
        'CREATE INDEX IF NOT EXISTS idx_admin_district_admin ON admin_district_assignments (admin_id)',
        'CREATE INDEX IF NOT EXISTS idx_admin_district_district ON admin_district_assignments (district_id)',
        'CREATE INDEX IF NOT EXISTS idx_media_files_user ON media_files (user_id)',
        'CREATE INDEX IF NOT EXISTS idx_complaint_media_complaint ON complaint_media (complaint_id)',
        'CREATE INDEX IF NOT EXISTS idx_email_otp ON password_otps (email, otp)',
        'CREATE INDEX IF NOT EXISTS idx_user_notif_user_id ON user_notifications (user_id, is_read)',
        'CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_logs (admin_id)',
        'CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs (created_at)',
    ]
    for sql in stmts:
        raw_pg_cursor.execute(sql)


# ---------------------------------------------------------------------------
# Seed default head admin (idempotent – runs every startup)
# ---------------------------------------------------------------------------
def _seed_head_admin(cursor, conn):
    cursor.execute("SELECT id FROM users WHERE role = 'head' LIMIT 1")
    if not cursor.fetchone():
        head_hash = generate_password_hash('Head@1234')
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, is_active) "
            "VALUES (?, ?, ?, 'head', 1)",
            ('Head Admin', 'head@servonix.com', head_hash)
        )
        print("[DB SEED] Default head admin created: head@servonix.com / Head@1234")
    conn.commit()


# ---------------------------------------------------------------------------
# init_db  – called once on app startup
# ---------------------------------------------------------------------------
def init_db():
    """Create all tables and seed default data. Safe to call on every startup."""
    max_retries = 5
    delay = 1

    for attempt in range(max_retries):
        try:
            conn = get_db()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[DB] Connection failed (attempt {attempt+1}/{max_retries}), "
                      f"retrying in {delay}s… ({e})")
                time.sleep(delay)
                delay *= 2
            else:
                raise

    cursor = conn.cursor()

    if DATABASE_URL:
        # PostgreSQL: run DDL on the raw psycopg2 cursor to avoid RETURNING id injection
        raw_cursor = conn._conn.cursor()
        _create_tables_postgres(raw_cursor)
        conn._conn.commit()
        raw_cursor.close()
        print("[DB] PostgreSQL tables ready.")
    else:
        _create_tables_sqlite(cursor)
        conn.commit()
        print("[DB] SQLite tables ready.")

    _seed_head_admin(cursor, conn)
    cursor.close()
    conn.close()
    print("[DB] Initialization complete.")


__all__ = ['get_db', 'init_db']

