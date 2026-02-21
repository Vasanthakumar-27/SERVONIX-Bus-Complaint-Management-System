"""
Security rate limiting helpers
===============================
"""
from ..database.connection import get_db
from datetime import datetime, timedelta


def check_verification_rate_limit(email, otp_type='registration'):
    """
    Check if email has exceeded OTP verification attempt rate limit.
    
    Args:
        email: Email address
        otp_type: 'registration' or 'password_reset'
    
    Returns:
        (allowed: bool, retry_minutes: int)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Count attempts in last 5 minutes
    cursor.execute("""
        SELECT COUNT(*) as attempts 
        FROM otp_verification_attempts
        WHERE email = ? 
          AND otp_type = ?
          AND created_at > datetime('now', '-5 minutes')
    """, (email, otp_type))
    
    result = cursor.fetchone()
    attempts = result['attempts'] if result else 0
    
    if attempts >= 5:  # Max 5 attempts per 5 minutes
        cursor.close()
        conn.close()
        return False, 5
    
    cursor.close()
    conn.close()
    return True, 0


def log_verification_attempt(email, otp_type='registration'):
    """Log an OTP verification attempt"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO otp_verification_attempts (email, otp_type, created_at)
        VALUES (?, ?, datetime('now'))
    """, (email, otp_type))
    
    conn.commit()
    cursor.close()
    conn.close()


def check_login_rate_limit(email):
    """
    Check if email has exceeded login attempt rate limit.
    
    Returns:
        (allowed: bool, failed_count: int)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Count failed attempts in last 15 minutes
    cursor.execute("""
        SELECT COUNT(*) as failed_count 
        FROM login_attempts
        WHERE email = ? 
          AND success = 0
          AND created_at > datetime('now', '-15 minutes')
    """, (email,))
    
    result = cursor.fetchone()
    failed_count = result['failed_count'] if result else 0
    
    cursor.close()
    conn.close()
    
    # Allow if less than 5 failed attempts
    return failed_count < 5, failed_count


def log_login_attempt(email, success, ip_address=None):
    """Log a login attempt"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO login_attempts (email, success, ip_address, created_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (email, success, ip_address))
    
    conn.commit()
    cursor.close()
    conn.close()


def reset_login_attempts(email):
    """Reset login attempts after successful login"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM login_attempts 
        WHERE email = ? AND created_at < datetime('now', '-15 minutes')
    """, (email,))
    
    conn.commit()
    cursor.close()
    conn.close()
