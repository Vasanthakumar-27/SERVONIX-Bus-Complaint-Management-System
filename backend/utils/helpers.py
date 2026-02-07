"""Utility functions and helpers"""
from datetime import datetime
from flask import request
import mimetypes


def get_current_time():
    """Get current time in system's local timezone"""
    return datetime.now()


def format_datetime_for_db(dt=None):
    """Format datetime for SQLite storage (ISO format)"""
    if dt is None:
        dt = get_current_time()
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def get_current_timestamp_for_db():
    """Get current system timestamp formatted for database insertion"""
    return format_datetime_for_db(datetime.now())


def get_token_from_request():
    """Extract Bearer token from Authorization header"""
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        return auth.split(' ', 1)[1]
    return None


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_mime_type(filename):
    """Get MIME type for file"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def format_timestamp(value):
    """Format timestamp for display"""
    if not value:
        return None
    try:
        if isinstance(value, str):
            # Try standard SQLite format first
            try:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # Fallback to fromisoformat for ISO format
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return value


def clamp_limit(value, default=50, minimum=1, maximum=200):
    """Clamp pagination limit to safe range"""
    try:
        limit = int(value)
        return max(minimum, min(limit, maximum))
    except (TypeError, ValueError):
        return default


def reverse_route_name(route_name):
    """Reverse route name (e.g., 'A-B' becomes 'B-A')"""
    if not route_name or '-' not in route_name:
        return route_name
    parts = route_name.split('-')
    if len(parts) == 2:
        return f"{parts[1]}-{parts[0]}"
    return route_name
