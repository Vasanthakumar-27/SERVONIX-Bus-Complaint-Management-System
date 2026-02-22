import os
import sqlite3
import smtplib
from flask import Blueprint, current_app, jsonify, request
from ..database.connection import DB_PATH, get_db

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')


def _check_key():
    # Allow when DEBUG_API_KEY matches header or when FLASK_DEBUG env is true
    expected = os.environ.get('DEBUG_API_KEY')
    if expected:
        provided = request.headers.get('X-DEBUG-KEY', '')
        return provided == expected
    # fallback allow only when running in development mode
    return os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')


@debug_bp.route('/status', methods=['GET'])
def status():
    if not _check_key():
        return jsonify({'error': 'missing or invalid debug key'}), 403

    info = {'ok': True}

    # database tables
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','index') ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        info['db_objects'] = [{'name': r['name'], 'type': r['type']} for r in rows]
    except sqlite3.Error as e:
        info['db_error'] = str(e)

    # recent email dev log
    try:
        logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        log_path = os.path.join(logs_dir, 'email_dev.log')
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                data = f.read()
            # return only the last 2000 chars
            info['recent_email_log_tail'] = data[-2000:]
        else:
            info['recent_email_log_tail'] = ''
    except Exception as e:
        info['email_log_error'] = str(e)

    return jsonify(info)


@debug_bp.route('/email-status', methods=['GET'])
def email_status():
    """Show current email configuration (no passwords)."""
    if not _check_key():
        return jsonify({'error': 'missing or invalid debug key'}), 403
    from ..services.email_service import EmailService
    svc = EmailService()
    return jsonify(svc.get_status())


@debug_bp.route('/email-test', methods=['POST'])
def email_test():
    """
    Test SMTP/Resend connectivity and optionally send a test OTP email.
    Body (JSON, optional): { "to": "recipient@example.com" }
    If "to" not given, only tests the connection without sending.
    """
    if not _check_key():
        return jsonify({'error': 'missing or invalid debug key'}), 403

    from ..services.email_service import EmailService
    svc = EmailService()

    # Connection test
    ok, msg = svc.test_smtp_connection()
    result = {
        'connection_ok': ok,
        'connection_message': msg,
        'config': svc.get_status(),
    }

    # Optional: send a real test email
    to_email = (request.get_json() or {}).get('to', '').strip()
    if to_email and ok:
        sent = svc._send_email(
            to_email,
            '🔧 SERVONIX Email Test',
            '<h2>Email delivery test</h2><p>If you see this, SMTP is working correctly.</p>'
        )
        result['test_email_sent'] = sent
        result['test_email_to'] = to_email

    return jsonify(result), 200 if ok else 500
