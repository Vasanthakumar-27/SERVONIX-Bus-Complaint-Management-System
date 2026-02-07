"""Authentication routes with secure OTP system"""
from flask import Blueprint, request, jsonify
import logging
import secrets
import hashlib
import hmac
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

from auth.utils import create_user, authenticate_user
from utils.helpers import get_current_timestamp_for_db
from utils.decorators import require_user_auth
from database.connection import get_db
import re

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# Security Configuration
OTP_EXPIRY_MINUTES = 5  # OTP expires in 5 minutes
OTP_RATE_LIMIT_MAX = 3  # Max 3 OTP requests
OTP_RATE_LIMIT_WINDOW = 10  # Per 10 minutes
OTP_LENGTH = 6

# Dev mode - shows OTP in response for testing (set to False in production)
DEV_MODE = os.environ.get('FLASK_ENV', 'development') == 'development'

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def is_valid_email(email):
    """Validate email format"""
    return bool(EMAIL_REGEX.match(email))


def generate_secure_otp():
    """Generate a cryptographically secure 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])


def hash_otp(otp):
    """Hash OTP using SHA-256 for secure storage"""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(otp, otp_hash):
    """
    Verify OTP against stored hash using constant-time comparison.
    This prevents timing attacks that could be used to guess OTPs.
    """
    computed_hash = hashlib.sha256(otp.encode()).hexdigest()
    return hmac.compare_digest(computed_hash, otp_hash)



def check_rate_limit(email):
    """Check if email has exceeded OTP request rate limit"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get rate limit record
    cursor.execute("""
        SELECT id, request_count, window_start FROM otp_rate_limit 
        WHERE email = ?
    """, (email,))
    record = cursor.fetchone()
    
    now = datetime.now()
    
    if not record:
        # First request - create record
        cursor.execute("""
            INSERT INTO otp_rate_limit (email, request_count, window_start, last_request)
            VALUES (?, 1, ?, ?)
        """, (email, now.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        cursor.close()
        conn.close()
        return True, OTP_RATE_LIMIT_MAX - 1
    
    window_start = datetime.strptime(record['window_start'], '%Y-%m-%d %H:%M:%S')
    window_elapsed = (now - window_start).total_seconds() / 60
    
    if window_elapsed >= OTP_RATE_LIMIT_WINDOW:
        # Reset window
        cursor.execute("""
            UPDATE otp_rate_limit 
            SET request_count = 1, window_start = ?, last_request = ?
            WHERE id = ?
        """, (now.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S'), record['id']))
        conn.commit()
        cursor.close()
        conn.close()
        return True, OTP_RATE_LIMIT_MAX - 1
    
    if record['request_count'] >= OTP_RATE_LIMIT_MAX:
        # Rate limit exceeded
        remaining_time = OTP_RATE_LIMIT_WINDOW - window_elapsed
        cursor.close()
        conn.close()
        return False, remaining_time
    
    # Increment counter
    cursor.execute("""
        UPDATE otp_rate_limit 
        SET request_count = request_count + 1, last_request = ?
        WHERE id = ?
    """, (now.strftime('%Y-%m-%d %H:%M:%S'), record['id']))
    conn.commit()
    remaining = OTP_RATE_LIMIT_MAX - record['request_count'] - 1
    cursor.close()
    conn.close()
    return True, remaining


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (legacy - direct registration)"""
    data = request.get_json() or {}
    if not all(data.get(k) for k in ('name', 'email', 'password')):
        return jsonify({'error': 'missing fields'}), 400
    try:
        res = create_user(data['name'], data['email'], data['password'])
        return jsonify(res), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ============================================================
# SECURE REGISTRATION OTP SYSTEM
# ============================================================

@auth_bp.route('/register-request', methods=['POST'])
def register_request():
    """
    STEP 1: Request registration with OTP verification
    - Validates inputs
    - Checks if email already exists
    - Generates and sends OTP
    - Stores pending registration (not actual user yet)
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    
    # Validate inputs
    if not name or len(name) < 2:
        return jsonify({'error': 'Name must be at least 2 characters'}), 400
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if not password or len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if len(password) > 128:
        return jsonify({'error': 'Password too long'}), 400
    
    # Get client IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if email already exists in users table
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Email is already registered. Please login.'}), 409
        
        # Check rate limiting
        allowed, remaining = check_rate_limit(email)
        if not allowed:
            cursor.close()
            conn.close()
            logger.warning(f"Registration rate limit exceeded for {email}")
            return jsonify({
                'error': f'Too many attempts. Please try again in {int(remaining)} minutes.',
                'retry_after': int(remaining)
            }), 429
        
        # Generate secure OTP
        otp = generate_secure_otp()
        otp_hashed = hash_otp(otp)
        password_hashed = generate_password_hash(password)
        expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        
        # Delete any existing pending registration for this email
        cursor.execute("DELETE FROM registration_otp WHERE email = ?", (email,))
        
        # Store pending registration with hashed OTP
        cursor.execute("""
            INSERT INTO registration_otp (name, email, password_hash, otp_hash, expires_at, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, password_hashed, otp_hashed, expires_at.strftime('%Y-%m-%d %H:%M:%S'), client_ip))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Send OTP via email
        from services.email_service import email_service
        email_sent = email_service.send_registration_otp_email(email, otp, name)
        
        if email_sent:
            logger.info(f"Registration OTP sent to {email}")
            response_data = {
                'message': 'Verification code sent to your email',
                'email': email,
                'expires_in': OTP_EXPIRY_MINUTES
            }
            # Include OTP in dev mode for testing
            if DEV_MODE:
                response_data['dev_otp'] = otp
                logger.info(f"[DEV MODE] Registration OTP for {email}: {otp}")
            return jsonify(response_data), 200
        else:
            logger.error(f"Failed to send registration OTP to {email}")
            return jsonify({'error': 'Failed to send verification email. Please try again.'}), 500
        
    except Exception as e:
        logger.error(f"Error in register_request: {str(e)}")
        return jsonify({'error': 'Failed to process registration'}), 500


@auth_bp.route('/register-verify', methods=['POST'])
def register_verify():
    """
    STEP 2: Verify OTP and create user account
    - Validates OTP
    - Creates user in database
    - Deletes pending registration
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    otp = data.get('otp', '').strip()
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
    
    # Validate OTP format
    if not otp.isdigit() or len(otp) != OTP_LENGTH:
        return jsonify({'error': 'Invalid OTP format'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get pending registration
        cursor.execute("""
            SELECT id, name, email, password_hash, otp_hash, expires_at 
            FROM registration_otp 
            WHERE email = ?
        """, (email,))
        
        pending = cursor.fetchone()
        
        if not pending:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No pending registration found. Please register again.'}), 400
        
        # Verify OTP hash
        if not verify_otp_hash(otp, pending['otp_hash']):
            cursor.close()
            conn.close()
            logger.warning(f"Invalid registration OTP for {email}")
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Check expiry
        expires_at = datetime.strptime(pending['expires_at'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expires_at:
            # Delete expired pending registration
            cursor.execute("DELETE FROM registration_otp WHERE id = ?", (pending['id'],))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'error': 'Verification code has expired. Please register again.'}), 400
        
        # Check if email was registered while OTP was pending
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM registration_otp WHERE id = ?", (pending['id'],))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'error': 'Email is already registered. Please login.'}), 409
        
        # Create user account
        import secrets
        import string
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
        
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, token, created_at)
            VALUES (?, ?, ?, 'user', ?, datetime('now'))
        """, (pending['name'], pending['email'], pending['password_hash'], token))
        
        user_id = cursor.lastrowid
        
        # Delete pending registration
        cursor.execute("DELETE FROM registration_otp WHERE id = ?", (pending['id'],))
        
        # Reset rate limit for this email
        cursor.execute("DELETE FROM otp_rate_limit WHERE email = ?", (email,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User registered successfully: {email}")
        
        return jsonify({
            'message': 'Registration successful! You can now login.',
            'user': {
                'id': user_id,
                'name': pending['name'],
                'email': pending['email']
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error in register_verify: {str(e)}")
        return jsonify({'error': 'Failed to complete registration'}), 500


@auth_bp.route('/register-resend', methods=['POST'])
def register_resend():
    """
    Resend registration OTP
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get pending registration
        cursor.execute("""
            SELECT id, name FROM registration_otp WHERE email = ?
        """, (email,))
        
        pending = cursor.fetchone()
        
        if not pending:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No pending registration found'}), 400
        
        # Check rate limiting
        allowed, remaining = check_rate_limit(email)
        if not allowed:
            cursor.close()
            conn.close()
            return jsonify({
                'error': f'Too many attempts. Please try again in {int(remaining)} minutes.',
                'retry_after': int(remaining)
            }), 429
        
        # Generate new OTP
        otp = generate_secure_otp()
        otp_hashed = hash_otp(otp)
        expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        
        # Update pending registration with new OTP
        cursor.execute("""
            UPDATE registration_otp 
            SET otp_hash = ?, expires_at = ?, created_at = datetime('now')
            WHERE id = ?
        """, (otp_hashed, expires_at.strftime('%Y-%m-%d %H:%M:%S'), pending['id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Send OTP via email
        from services.email_service import email_service
        email_sent = email_service.send_registration_otp_email(email, otp, pending['name'])
        
        if email_sent:
            response_data = {
                'message': 'New verification code sent',
                'expires_in': OTP_EXPIRY_MINUTES
            }
            # Include OTP in dev mode for testing
            if DEV_MODE:
                response_data['dev_otp'] = otp
                logger.info(f"[DEV MODE] Resend Registration OTP for {email}: {otp}")
            return jsonify(response_data), 200
        else:
            return jsonify({'error': 'Failed to send email'}), 500
        
    except Exception as e:
        logger.error(f"Error in register_resend: {str(e)}")
        return jsonify({'error': 'Failed to resend OTP'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json() or {}
        logger.info(f"Login attempt for email: {data.get('email')}")
        
        if not all(data.get(k) for k in ('email', 'password')):
            logger.warning("Login failed: missing fields")
            return jsonify({'error': 'missing fields'}), 400
        
        res = authenticate_user(data['email'], data['password'])
        if not res:
            logger.warning(f"Login failed: invalid credentials for {data.get('email')}")
            return jsonify({'error': 'invalid credentials'}), 401
        
        logger.info(f"Login successful for {data.get('email')} with role {res.get('role')}")
        return jsonify(res)
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}'}), 500


# ============================================================
# SECURE OTP SYSTEM FOR PASSWORD RESET
# ============================================================


@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user profile (works for user, admin, and head roles)"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'authentication required'}), 401
        
        profile_data = {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'phone': user.get('phone'),
            'district': user.get('district'),
            'created_at': user.get('created_at'),
            'profile_pic': user.get('profile_pic'),
            'last_active': user.get('last_active')
        }
        
        # If user is admin, fetch assigned districts and routes
        if user['role'] == 'admin':
            try:
                conn = get_db()
                cursor = conn.cursor()
                
                # Get admin assignments with district and route info
                cursor.execute("""
                    SELECT DISTINCT d.name as district_name, r.name as route_name
                    FROM admin_assignments aa
                    LEFT JOIN districts d ON aa.district_id = d.id
                    LEFT JOIN routes r ON aa.route_id = r.id
                    WHERE aa.admin_id = ?
                    ORDER BY d.name, r.name
                """, (user['id'],))
                
                assignments = cursor.fetchall()
                
                # Group assignments
                districts = set()
                routes = set()
                
                for assignment in assignments:
                    if assignment['district_name']:
                        districts.add(assignment['district_name'])
                    if assignment['route_name']:
                        routes.add(assignment['route_name'])
                
                profile_data['assigned_districts'] = ', '.join(sorted(districts)) if districts else 'Not assigned'
                profile_data['assigned_routes'] = ', '.join(sorted(routes)) if routes else 'Not assigned'
                
                cursor.close()
                conn.close()
                
            except Exception as assign_error:
                logger.warning(f"Error fetching admin assignments: {assign_error}")
                profile_data['assigned_districts'] = 'Error loading'
                profile_data['assigned_routes'] = 'Error loading'
        
        return jsonify(profile_data)
    except Exception as e:
        logger.error(f"Error in get_profile: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@auth_bp.route('/request-otp', methods=['POST'])
def request_otp():
    """
    STEP 1: Request OTP for password reset
    - Validates email exists
    - Checks rate limiting
    - Generates secure OTP
    - Hashes OTP before storage
    - Sends OTP via email
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Get client IP for logging
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, name, is_active FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            # Security: Don't reveal if email exists or not
            return jsonify({'message': 'If the email is registered, an OTP will be sent'}), 200
        
        if not user['is_active']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Account is deactivated. Contact support.'}), 403
        
        cursor.close()
        conn.close()
        
        # Check rate limiting
        allowed, remaining = check_rate_limit(email)
        if not allowed:
            logger.warning(f"Rate limit exceeded for {email} from IP {client_ip}")
            return jsonify({
                'error': f'Too many OTP requests. Please try again in {int(remaining)} minutes.',
                'retry_after': int(remaining)
            }), 429
        
        # Generate secure OTP
        otp = generate_secure_otp()
        otp_hashed = hash_otp(otp)
        expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Invalidate all previous OTPs for this email
        cursor.execute("UPDATE password_reset_otp SET used = 1 WHERE email = ? AND used = 0", (email,))
        
        # Store new hashed OTP
        cursor.execute("""
            INSERT INTO password_reset_otp (email, otp_hash, expires_at, used, ip_address)
            VALUES (?, ?, ?, 0, ?)
        """, (email, otp_hashed, expires_at.strftime('%Y-%m-%d %H:%M:%S'), client_ip))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Send OTP via email (plain OTP, not hash)
        from services.email_service import email_service
        email_sent = email_service.send_otp_email(email, otp, user['name'])
        
        if email_sent:
            logger.info(f"Password reset OTP sent to {email} from IP {client_ip}")
            response_data = {
                'message': 'OTP sent successfully to your email',
                'email': email,
                'expires_in': OTP_EXPIRY_MINUTES,
                'requests_remaining': remaining
            }
            # Include OTP in dev mode for testing
            if DEV_MODE:
                response_data['dev_otp'] = otp
                logger.info(f"[DEV MODE] Password Reset OTP for {email}: {otp}")
            return jsonify(response_data), 200
        else:
            logger.error(f"Failed to send OTP email to {email}")
            return jsonify({'error': 'Failed to send OTP email. Please try again.'}), 500
        
    except Exception as e:
        logger.error(f"Error in request_otp: {str(e)}")
        return jsonify({'error': 'Failed to process request'}), 500


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """
    STEP 2: Verify OTP
    - Validates OTP against hash
    - Checks expiry
    - Checks if already used
    - Returns verification token for password reset
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    otp = data.get('otp', '').strip()
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
    
    # Validate OTP format
    if not otp.isdigit() or len(otp) != OTP_LENGTH:
        return jsonify({'error': 'Invalid OTP format'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get the latest unused OTP for this email
        cursor.execute("""
            SELECT id, otp_hash, expires_at FROM password_reset_otp 
            WHERE email = ? AND used = 0
            ORDER BY created_at DESC LIMIT 1
        """, (email,))
        
        otp_record = cursor.fetchone()
        
        if not otp_record:
            cursor.close()
            conn.close()
            logger.warning(f"Invalid OTP attempt for {email} - no active OTP found")
            return jsonify({'error': 'Invalid OTP. Please request a new one.'}), 400
        
        # Verify OTP hash
        if not verify_otp_hash(otp, otp_record['otp_hash']):
            cursor.close()
            conn.close()
            logger.warning(f"Invalid OTP attempt for {email} - hash mismatch")
            return jsonify({'error': 'Invalid OTP'}), 400
        
        # Check expiry
        expires_at = datetime.strptime(otp_record['expires_at'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expires_at:
            # Mark as used to prevent further attempts
            cursor.execute("UPDATE password_reset_otp SET used = 1 WHERE id = ?", (otp_record['id'],))
            conn.commit()
            cursor.close()
            conn.close()
            logger.warning(f"Expired OTP attempt for {email}")
            return jsonify({'error': 'OTP has expired. Please request a new one.'}), 400
        
        # Generate a verification token (single-use token for password reset)
        verification_token = secrets.token_urlsafe(32)
        verification_hash = hashlib.sha256(verification_token.encode()).hexdigest()
        
        # Store verification token hash in the OTP record
        cursor.execute("""
            UPDATE password_reset_otp 
            SET otp_hash = ? 
            WHERE id = ?
        """, (verification_hash, otp_record['id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"OTP verified successfully for {email}")
        
        return jsonify({
            'message': 'OTP verified successfully',
            'verification_token': verification_token
        }), 200
            
    except Exception as e:
        logger.error(f"Error in verify_otp: {str(e)}")
        return jsonify({'error': 'Failed to verify OTP'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    STEP 3: Reset password after OTP verification
    - Validates verification token
    - Updates password
    - Invalidates all OTPs for the email
    - Prevents replay attacks
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    verification_token = data.get('verification_token', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not all([email, verification_token, new_password]):
        return jsonify({'error': 'Email, verification token, and new password are required'}), 400
    
    # Password validation
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if len(new_password) > 128:
        return jsonify({'error': 'Password too long'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Hash the verification token
        verification_hash = hashlib.sha256(verification_token.encode()).hexdigest()
        
        # Find the OTP record with matching verification token
        cursor.execute("""
            SELECT id FROM password_reset_otp 
            WHERE email = ? AND otp_hash = ? AND used = 0
            AND expires_at > datetime('now', 'localtime')
            ORDER BY created_at DESC LIMIT 1
        """, (email, verification_hash))
        
        otp_record = cursor.fetchone()
        
        if not otp_record:
            cursor.close()
            conn.close()
            logger.warning(f"Invalid password reset attempt for {email} - invalid verification token")
            return jsonify({'error': 'Invalid or expired session. Please request a new OTP.'}), 400
        
        # Get user
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Hash new password and update
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_password, user['id']))
        
        # Invalidate ALL OTPs for this email (prevents replay attacks)
        cursor.execute('DELETE FROM password_reset_otp WHERE email = ?', (email,))
        
        # Reset rate limit for this email
        cursor.execute('DELETE FROM otp_rate_limit WHERE email = ?', (email,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Password reset successfully for {email}")
        
        return jsonify({'message': 'Password reset successfully. You can now login.'}), 200
            
    except Exception as e:
        logger.error(f"Error in reset_password: {str(e)}")
        return jsonify({'error': 'Failed to reset password'}), 500


# Legacy endpoint for backward compatibility
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Redirect to new request-otp endpoint"""
    return request_otp()


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change password for authenticated user"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'authentication required'}), 401
        
        data = request.get_json() or {}
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400
        
        auth_result = authenticate_user(user['email'], current_password)
        if not auth_result:
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        from database.connection import get_db
        conn = get_db()
        cursor = conn.cursor()
        
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_password, user['id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error in change_password: {str(e)}")
        return jsonify({'error': 'Failed to change password'}), 500
