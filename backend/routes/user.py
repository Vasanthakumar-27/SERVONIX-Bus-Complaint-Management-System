"""User-specific routes"""
from flask import Blueprint, request, jsonify
import logging
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from database.connection import get_db
from utils.decorators import require_user_auth
from config import config

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, url_prefix='/api/user')


@user_bp.route('/profile-picture', methods=['POST'])
def update_profile_picture():
    """Upload and update user profile picture"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
        
        # Create profile pics directory
        profile_pics_dir = os.path.join(config.UPLOAD_FOLDER, 'profile_pics')
        os.makedirs(profile_pics_dir, exist_ok=True)
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(profile_pics_dir, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Update database
        conn = get_db()
        cursor = conn.cursor()
        
        relative_path = f"uploads/profile_pics/{unique_filename}"
        cursor.execute(
            "UPDATE users SET profile_pic = ? WHERE id = ?",
            (relative_path, user['id'])
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Profile picture updated for user {user['id']}: {relative_path}")
        return jsonify({
            'message': 'Profile picture updated successfully',
            'profile_pic': f"/{relative_path}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating profile picture: {str(e)}")
        return jsonify({'error': 'Failed to update profile picture'}), 500


@user_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password (requires current password)"""
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
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get current password hash
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user['id'],)
        )
        user_record = cursor.fetchone()
        
        if not user_record or not check_password_hash(user_record['password_hash'], current_password):
            cursor.close()
            conn.close()
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        new_hash = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user['id'])
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User {user['id']} changed password successfully")
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return jsonify({'error': 'Failed to change password'}), 500


@user_bp.route('/update-phone', methods=['POST'])
def update_phone():
    """Update user phone number"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401
    
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    
    # Basic phone validation (optional - can be empty to remove)
    if phone and len(phone) < 10:
        return jsonify({'error': 'Phone number must be at least 10 digits'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET phone = ? WHERE id = ?",
            (phone if phone else None, user['id'])
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Phone updated for user {user['id']}")
        return jsonify({
            'message': 'Phone number updated successfully',
            'phone': phone
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating phone: {str(e)}")
        return jsonify({'error': 'Failed to update phone number'}), 500


@user_bp.route('/logout-all-devices', methods=['POST'])
def logout_all_devices():
    """Logout from all devices by invalidating all tokens"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Clear the token to invalidate all sessions
        cursor.execute(
            "UPDATE users SET token = NULL WHERE id = ?",
            (user['id'],)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User {user['id']} logged out from all devices")
        return jsonify({'message': 'Successfully logged out from all devices'}), 200
        
    except Exception as e:
        logger.error(f"Error logging out all devices: {str(e)}")
        return jsonify({'error': 'Failed to logout from all devices'}), 500


@user_bp.route('/notifications', methods=['GET'])
def get_user_notifications():
    """Fetch user notifications"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401

    include_read = (request.args.get('include_read', 'true').lower() != 'false')
    limit = int(request.args.get('limit', 50))

    conn = get_db()
    cursor = conn.cursor()
    
    query = '''
        SELECT id, type, message, related_id, is_read, created_at
        FROM user_notifications
        WHERE user_id = ?
    '''
    params = [user['id']]
    
    if not include_read:
        query += ' AND is_read = 0'
    
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    notifications = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return jsonify({'notifications': notifications})


@user_bp.route('/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_user_notification_read(notification_id):
    """Mark a user notification as read"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_notifications
        SET is_read = 1
        WHERE id = ? AND user_id = ?
    """, (notification_id, user['id']))
    updated = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if updated:
        return jsonify({'ok': True}), 200
    else:
        return jsonify({'error': 'not found or already read'}), 404


@user_bp.route('/notifications/mark-all-read', methods=['PUT'])
def mark_all_notifications_read():
    """Mark all user notifications as read"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_notifications
        SET is_read = 1
        WHERE user_id = ? AND is_read = 0
    """, (user['id'],))
    updated = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': f'{updated} notifications marked as read'}), 200
