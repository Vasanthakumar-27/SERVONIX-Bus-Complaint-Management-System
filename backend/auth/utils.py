"""Authentication utility functions"""
import secrets
import string
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from ..database.connection import get_db


def generate_token(length=64):
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_user(name, email, password, role='user', created_by=None, phone=None):
    """Create a new user in the database"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if email already exists
    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise ValueError(f"Email '{email}' is already registered")
    
    password_hash = generate_password_hash(password)
    token = generate_token()
    
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, token, created_by, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (name, email, password_hash, role, token, created_by, phone))
    
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    return {
        'id': user_id,
        'token': token,
        'role': role,
        'name': name,
        'email': email
    }


def authenticate_user(email, password):
    """Authenticate user with email and password"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email=? AND is_active=1", (email,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return None
        
    if not check_password_hash(user['password_hash'], password):
        cursor.close()
        conn.close()
        return None
    
    # Generate new token for session
    token = generate_token()
    cursor.execute("UPDATE users SET token=?, last_active=datetime('now') WHERE id=?", (token, user['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'id': user['id'],
        'token': token,
        'name': user['name'],
        'email': user['email'],
        'role': user['role'],
        'phone': user['phone'] if user['phone'] else None
    }


def get_user_by_token(token):
    """Get user by authentication token"""
    if not token:
        return None
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, role, phone, created_at, profile_pic
            FROM users 
            WHERE token=? AND is_active=1
        """, (token,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        print(f"Error getting user by token: {e}")
        return None


def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, role, phone, created_at, profile_pic, is_active
            FROM users 
            WHERE id=?
        """, (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None


def change_password(user_id, old_password, new_password):
    """Change user password"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT password_hash FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    
    if not user or not check_password_hash(user['password_hash'], old_password):
        cursor.close()
        conn.close()
        return False
    
    password_hash = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return True


def require_role(token, required_roles):
    """Check if user has required role(s)"""
    user = get_user_by_token(token)
    if not user:
        return None
    if user['role'] in required_roles:
        return user
    return None


__all__ = [
    'generate_token',
    'create_user',
    'authenticate_user',
    'get_user_by_token',
    'get_user_by_id',
    'change_password',
    'require_role'
]
