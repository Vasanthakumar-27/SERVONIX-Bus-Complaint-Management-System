"""Authentication routes with secure OTP system"""
from flask import Blueprint, request, jsonify
import logging
import secrets
import hashlib
import hmac
import os
import jwt as pyjwt
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

from ..auth.utils import create_user, authenticate_user
from ..utils.helpers import get_current_timestamp_for_db
from ..utils.decorators import require_user_auth
from ..database.connection import get_db
import re

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# Security Configuration
OTP_EXPIRY_MINUTES = 5  # OTP expires in 5 minutes
OTP_RATE_LIMIT_MAX = 3  # Max 3 OTP requests
OTP_RATE_LIMIT_WINDOW = 10  # Per 10 minutes
OTP_LENGTH = 6


def _jwt_secret():
    """Return the JWT signing secret. Falls back to SECRET_KEY."""
    return os.environ.get('JWT_SECRET') or os.environ.get('SECRET_KEY') or 'servonix-secret-key-change-in-production'


def _create_registration_token(name, email, password_hash, otp_hash, expires_at_str):
    """Return a signed JWT encoding the pending registration so it survives server restarts."""
    payload = {
        'type': 'pending_registration',
        'name': name,
        'email': email,
        'password_hash': password_hash,
        'otp_hash': otp_hash,
        'expires_at': expires_at_str,
        'exp': datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES + 2),  # slight grace period
    }
    return pyjwt.encode(payload, _jwt_secret(), algorithm='HS256')


def _decode_registration_token(token):
    """Decode and return the registration token payload, or None if invalid/expired."""
    try:
        payload = pyjwt.decode(token, _jwt_secret(), algorithms=['HS256'])
        if payload.get('type') != 'pending_registration':
            logger.warning(f"[JWT] Token type mismatch: expected 'pending_registration', got '{payload.get('type')}'")
            return None
        logger.info(f"[JWT] Token decoded successfully for {payload.get('email')}")
        return payload
    except Exception as e:
        logger.error(f"[JWT] Token decode failed: {type(e).__name__}: {str(e)}")
        return None


def _is_email_configured():
    """Re-read env vars at request time — avoids stale import-time constants."""
    return bool(os.environ.get('RESEND_API_KEY', '')) or bool(os.environ.get('EMAIL_PASSWORD', ''))


def _get_email_service():
    """Return a fresh EmailService instance so it always uses current env vars."""
    from ..services.email_service import EmailService
    return EmailService()

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def is_valid_email(email):
    """Validate email format"""
    return bool(EMAIL_REGEX.match(email))


@auth_bp.route('/email-status', methods=['GET'])
def email_status():
    """
    Public diagnostic endpoint — shows email config mode (no passwords).
    Visit: /api/email-status
    """
    svc = _get_email_service()
    return jsonify(svc.get_status())


@auth_bp.route('/email-test', methods=['POST'])
def email_test():
    """
    Test email connectivity.
    POST body (optional): {"to": "recipient@example.com"}
    """
    svc = _get_email_service()
    ok, msg = svc.test_smtp_connection()
    result = {'connection_ok': ok, 'connection_message': msg, 'config': svc.get_status()}
    to_email = (request.get_json() or {}).get('to', '').strip()
    if to_email and ok:
        sent = svc._send_email(
            to_email,
            '🔧 SERVONIX Email Test',
            '<h2>Email test</h2><p>If you see this, SMTP is working correctly.</p>'
        )
        result['test_email_sent'] = sent
        result['test_email_to'] = to_email
    return jsonify(result), (200 if ok else 500)


@auth_bp.route('/email-diagnose', methods=['GET'])
def email_diagnose():
    """
    Comprehensive email diagnostics endpoint.
    Provides detailed information about email configuration and troubleshooting steps.
    """
    svc = _get_email_service()
    status = svc.get_status()
    conn_ok, conn_msg = svc.test_smtp_connection()
    
    diagnostics = {
        'timestamp': datetime.now().isoformat(),
        'status': status,
        'connection_test': {
            'ok': conn_ok,
            'message': conn_msg
        },
        'troubleshooting': []
    }
    
    if not conn_ok:
        if status.get('mode') == 'development':
            diagnostics['troubleshooting'].append({
                'issue': 'Development mode - no email credentials configured',
                'solution': 'Set EMAIL_PASSWORD in .env and restart the server'
            })
        elif status.get('mode') == 'resend':
            if status.get('sandbox'):
                diagnostics['troubleshooting'].append({
                    'issue': 'Resend sandbox - only delivers to account owner',
                    'solution': 'Set RESEND_FROM to a verified domain address in .env'
                })
            else:
                diagnostics['troubleshooting'].append({
                    'issue': 'Resend API key issue',
                    'solution': 'Check RESEND_API_KEY in .env is correct'
                })
        elif status.get('mode') == 'smtp':
            if 'port' in conn_msg.lower() or 'connect' in conn_msg.lower():
                diagnostics['troubleshooting'].append({
                    'issue': 'Cannot connect to SMTP server (port blocked)',
                    'solution': 'Use Resend API instead: set RESEND_API_KEY in .env',
                    'resend_signup_url': 'https://resend.com'
                })
            elif 'authentication' in conn_msg.lower():
                diagnostics['troubleshooting'].append({
                    'issue': 'SMTP authentication failed',
                    'solution': 'Check EMAIL_SENDER and EMAIL_PASSWORD in .env. Use Gmail App Password, not your account password.'
                })
            else:
                diagnostics['troubleshooting'].append({
                    'issue': 'SMTP connection error',
                    'solution': 'Check all SMTP settings and email credentials in .env'
                })
    else:
        diagnostics['troubleshooting'].append({
            'status': 'Email service is working correctly',
            'message': 'OTP emails should be delivered successfully'
        })
    
    return jsonify(diagnostics), 200


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
    is_valid = hmac.compare_digest(computed_hash, otp_hash)
    logger.debug(f"[OTP_HASH] OTP: {otp}, computed_hash: {computed_hash[:20]}..., stored_hash: {otp_hash[:20] if otp_hash else 'None'}..., match: {is_valid}")
    return is_valid



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
        
        # Store pending registration with hashed OTP
        try:
            cursor.execute("DELETE FROM registration_otp WHERE email = ?", (email,))
            #  DEBUG: Log plain OTP temporarily for testing (REMOVE IN PRODUCTION)
            logger.info(f"[DEV-OTP] Registration OTP for {email}: {otp}")
            
            cursor.execute("""
                INSERT INTO registration_otp (name, email, password_hash, otp_hash, expires_at, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, email, password_hashed, otp_hashed, expires_at.strftime('%Y-%m-%d %H:%M:%S'), client_ip))
            conn.commit()
        except Exception as db_err:
            logger.warning(f"[register-request] DB insert failed (will rely on token): {db_err}")
        cursor.close()
        conn.close()
        
        # Send OTP via email
        email_service = _get_email_service()
        email_send_failed = False
        
        try:
            # Try to send OTP via email
            if email_service.development_mode:
                # Development mode - log the OTP to console/file for testing
                email_service.send_registration_otp_email(email, otp, name)
                logger.info(f"[OTP-DEV] Development mode - OTP sent to console/logs for {email}")
                # In dev mode, don't mark as failed - allow registration to proceed
                # Developers/testers can use the OTP from console logs
            elif email_service.resend_api_key:
                # Resend API configured
                _ok = email_service.send_registration_otp_email(email, otp, name)
                if _ok:
                    logger.info(f"[OTP] Registration OTP sent successfully via Resend to {email}")
                else:
                    email_send_failed = True
                    logger.error(f"[OTP] Failed to send registration OTP via Resend to {email}")
            else:
                # SMTP configured
                _ok = email_service.send_registration_otp_email(email, otp, name)
                if _ok:
                    logger.info(f"[OTP] Registration OTP sent successfully via SMTP to {email}")
                else:
                    email_send_failed = True
                    logger.error(f"[OTP] Failed to send registration OTP via SMTP to {email}")
        except Exception as e:
            email_send_failed = True
            logger.error(f"[OTP] Exception sending registration OTP: {str(e)}")

        # Build response — also include a signed registration_token so verify works
        # even if the server restarts and the DB row is lost (Render free tier).
        registration_token = _create_registration_token(
            name, email, password_hashed, otp_hashed, expires_at.strftime('%Y-%m-%d %H:%M:%S')
        )

        response_data = {
            'email': email,
            'expires_in': OTP_EXPIRY_MINUTES,
            'registration_token': registration_token,
        }
        
        if email_send_failed:
            # Email delivery failed (production environment) - let frontend know
            response_data['message'] = 'Failed to send verification code to email. Please check your email configuration or contact support.'
            response_data['email_failed'] = True
            logger.error(f"[OTP] Registration email failed for {email}")
            return jsonify(response_data), 400  # Return 400 only on actual email failure
        elif email_service.development_mode:
            # Development mode - OTP is in console/logs
            response_data['message'] = 'Verification code sent to your email (check console logs for OTP in development mode)'
            response_data['development_mode'] = True
            logger.info(f"[OTP] Registration OTP request processed in development mode for {email}")
            return jsonify(response_data), 200
        else:
            # Email sent successfully in production
            response_data['message'] = 'Verification code sent to your email'
            logger.info(f"[OTP] Registration OTP sent to {email}")
            return jsonify(response_data), 200
        
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
    registration_token = data.get('registration_token', '').strip()
    
    # DEBUG: Log incoming request
    logger.info(f"[register-verify] Incoming request - email: {email}, otp_length: {len(otp)}, has_token: {bool(registration_token)}")
    
    if not email or not otp:
        logger.warning(f"[register-verify] Missing email or otp - email_empty: {not email}, otp_empty: {not otp}")
        return jsonify({'error': 'Email and OTP are required'}), 400
    
    # Validate OTP format
    if not otp.isdigit() or len(otp) != OTP_LENGTH:
        logger.warning(f"[register-verify] Invalid OTP format - isdigit: {otp.isdigit()}, len: {len(otp)}")
        return jsonify({'error': 'Invalid OTP format'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()

        # --- Primary path: decode signed registration_token (survives server restarts) ---
        token_payload = _decode_registration_token(registration_token) if registration_token else None
        
        logger.info(f"[register-verify] Token decode result - has_token: {bool(registration_token)}, decode_success: {token_payload is not None}")
        if token_payload:
            logger.info(f"[register-verify] Token payload email: {token_payload.get('email')}, request email: {email}")

        if token_payload and token_payload.get('email') == email:
            pending = token_payload  # use token data as the pending record
            pending_id = None  # no DB row to delete (or it may still exist)
            logger.info(f"[register-verify] Using registration_token for {email}")
        else:
            # --- Fallback: DB lookup ---
            logger.info(f"[register-verify] Token decode failed or email mismatch, falling back to DB lookup for {email}")
            cursor.execute("""
                SELECT id, name, email, password_hash, otp_hash, expires_at 
                FROM registration_otp 
                WHERE email = ?
            """, (email,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                conn.close()
                logger.error(f"[register-verify] No pending registration found in DB for {email} - 400 error")
                return jsonify({'error': 'No pending registration found. Please register again.'}), 400
            pending = dict(row)
            pending_id = pending['id']
            logger.info(f"[register-verify] Found pending registration in DB for {email}")
        
        # Verify OTP hash
        is_otp_valid = verify_otp_hash(otp, pending['otp_hash'])
        logger.info(f"[register-verify] OTP validation result: {is_otp_valid} for {email}")
        
        if not is_otp_valid:
            cursor.close()
            conn.close()
            logger.warning(f"[register-verify] Invalid registration OTP for {email} - 400 error")
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Check expiry
        expires_at = datetime.strptime(pending['expires_at'], '%Y-%m-%d %H:%M:%S')
        logger.info(f"[register-verify] OTP expires_at: {pending['expires_at']}, now: {datetime.now()}")
        
        if datetime.now() > expires_at:
            # Delete expired DB row if it exists
            if pending_id:
                cursor.execute("DELETE FROM registration_otp WHERE id = ?", (pending_id,))
                conn.commit()
            cursor.close()
            conn.close()
            logger.warning(f"[register-verify] OTP expired for {email} - 400 error")
            return jsonify({'error': 'Verification code has expired. Please register again.'}), 400
        
        # Check if email was registered while OTP was pending
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            if pending_id:
                cursor.execute("DELETE FROM registration_otp WHERE id = ?", (pending_id,))
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
        
        # Delete pending registration row (best effort)
        try:
            if pending_id:
                cursor.execute("DELETE FROM registration_otp WHERE id = ?", (pending_id,))
            else:
                cursor.execute("DELETE FROM registration_otp WHERE email = ?", (email,))
        except Exception:
            pass
        
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
    registration_token = data.get('registration_token', '').strip()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Resolve pending registration: token first, then DB fallback
        token_payload = _decode_registration_token(registration_token) if registration_token else None
        if token_payload and token_payload.get('email') == email:
            reg_name = token_payload['name']
            reg_password_hash = token_payload['password_hash']
            pending_id = None
        else:
            cursor.execute("SELECT id, name, password_hash FROM registration_otp WHERE email = ?", (email,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                conn.close()
                return jsonify({'error': 'No pending registration found'}), 400
            reg_name = row['name']
            reg_password_hash = row['password_hash']
            pending_id = row['id']
        
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
        expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
        
        # Update DB row if it exists (best effort)
        try:
            if pending_id:
                cursor.execute("""
                    UPDATE registration_otp 
                    SET otp_hash = ?, expires_at = ?, created_at = datetime('now')
                    WHERE id = ?
                """, (otp_hashed, expires_at_str, pending_id))
            else:
                # Re-insert in case DB was wiped (token was used)
                cursor.execute("DELETE FROM registration_otp WHERE email = ?", (email,))
                cursor.execute("""
                    INSERT INTO registration_otp (name, email, password_hash, otp_hash, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (reg_name, email, reg_password_hash, otp_hashed, expires_at_str))
            conn.commit()
        except Exception as db_err:
            logger.warning(f"[register-resend] DB update failed (will rely on token): {db_err}")
        cursor.close()
        conn.close()
        
        # Send OTP via email — same strategy as register_request
        # Send OTP via email
        email_service = _get_email_service()
        email_send_failed = False
        
        if email_service.resend_api_key:
            _ok = email_service.send_registration_otp_email(email, otp, reg_name)
            if not _ok:
                email_send_failed = True
                logger.error(f"[OTP] Failed to resend registration OTP to {email}")
        elif email_service.development_mode:
            email_service.send_registration_otp_email(email, otp, reg_name)
            email_send_failed = True
        else:
            # SMTP — send synchronously so failures are caught immediately
            _ok = email_service.send_registration_otp_email(email, otp, reg_name)
            if not _ok:
                email_send_failed = True
                logger.error(f"[OTP] Failed to resend registration OTP to {email}")
            else:
                logger.info(f"[OTP] Resend registration OTP sent to {email}")

        # Issue a fresh registration_token with the new OTP
        new_registration_token = _create_registration_token(
            reg_name, email, reg_password_hash, otp_hashed, expires_at_str
        )

        response_data = {
            'expires_in': OTP_EXPIRY_MINUTES,
            'registration_token': new_registration_token,
        }
        
        if email_send_failed:
            response_data['message'] = 'Failed to send new verification code. Please try again or contact support.'
            response_data['email_failed'] = True
            logger.error(f"[OTP] Resend registration OTP failed for {email}")
            return jsonify(response_data), 400
        else:
            response_data['message'] = 'New verification code sent to your email'
            logger.info(f"[OTP] Resend registration OTP sent to {email}")
            return jsonify(response_data), 200
        
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
        
        # Send OTP via email
        email_service = _get_email_service()
        email_send_failed = False
        
        try:
            if email_service.resend_api_key or not email_service.development_mode:
                _ok = email_service.send_otp_email(email, otp, user['name'])
                if _ok:
                    logger.info(f"[OTP] Password reset OTP sent successfully to {email}")
                else:
                    email_send_failed = True
                    logger.error(f"[OTP] Failed to send password reset OTP to {email}")
            else:
                email_service.send_otp_email(email, otp, user['name'])
                email_send_failed = True
                logger.info(f"[OTP] Development mode - Password reset OTP for {email}: {otp}")
        except Exception as e:
            email_send_failed = True
            logger.error(f"[OTP] Exception sending password reset OTP: {str(e)}")

        response_data = {
            'email': email,
            'expires_in': OTP_EXPIRY_MINUTES,
            'requests_remaining': remaining
        }
        
        if email_send_failed:
            response_data['message'] = 'Failed to send OTP to your email. Please check your email configuration or try again.'
            response_data['email_failed'] = True
            logger.error(f"[OTP] Password reset OTP failed for {email}")
            return jsonify(response_data), 400
        else:
            response_data['message'] = 'OTP sent successfully to your email'
            logger.info(f"[OTP] Password reset OTP sent to {email}")
            return jsonify(response_data), 200
        
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
        
        from ..database.connection import get_db
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


@auth_bp.route('/users/head', methods=['GET'])
def get_head_user():
    """Return the head admin's basic info for use as a message recipient.
    Accessible to authenticated admin/head users.
    """
    user = require_user_auth()
    if not user or user.get('role') not in ('admin', 'head'):
        return jsonify({'error': 'Authentication required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, email FROM users WHERE role = ? AND is_active = 1 LIMIT 1',
            ('head',)
        )
        head = cursor.fetchone()
        cursor.close()
        conn.close()

        if not head:
            return jsonify({'error': 'No active head user found'}), 404

        return jsonify({'user': dict(head)})

    except Exception as e:
        logger.error(f'Error fetching head user: {e}')
        return jsonify({'error': 'Failed to fetch head user'}), 500

# DEBUG ENDPOINT - Development testing only
@auth_bp.route('/debug-get-otp/<email>', methods=['GET'])
def debug_get_otp(email):
    """
    DEBUG ENDPOINT - Returns the OTP for a pending registration (development only)
    WARNING: Only use this for testing - remove in production
    """
    if os.environ.get('ENVIRONMENT') == 'production':
        return jsonify({'error': 'Not available in production'}), 403
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Find the OTP hash for this email
        cursor.execute("SELECT otp_hash, expires_at FROM registration_otp WHERE email = ? ORDER BY created_at DESC LIMIT 1", (email.lower(),))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return jsonify({'error': 'No pending registration found for this email'}), 404
        
        # This is a SECURITY RISK - only for development testing!
        # In production, the user must check their email
        logger.warning(f"[SECURITY] DEBUG endpoint called for {email} - remove this endpoint from production!")
        
        # Generate and return a test OTP for this hash
        # Try common test OTPs
        test_otps = ["123456", "000000", "999999", "111111", "222222"]
        for test_otp in test_otps:
            hash_attempt = hashlib.sha256(test_otp.encode()).hexdigest()
            if hmac.compare_digest(hash_attempt, row['otp_hash']):
                return jsonify({
                    'otp': test_otp,
                    'email': email,
                    'message': 'DEBUG ENDPOINT - This OTP was found by brute-force test (security issue!)'
                })
        
        return jsonify({'error': 'Could not find valid OTP (not in test list)'}), 400
    
    except Exception as e:
        logger.error(f'Debug endpoint error: {e}')
        return jsonify({'error': str(e)}), 500