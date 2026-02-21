"""
Admin-Head Messages Communication System
Secure internal messaging between Admin and Head
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
from datetime import datetime
from ..database.connection import get_db
import os
import logging

logger = logging.getLogger(__name__)

messages_bp = Blueprint('messages', __name__, url_prefix='/api/messages')

def get_user_from_token():
    """Extract user from JWT token"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None
    try:
        payload = jwt.decode(token, os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'), algorithms=['HS256'])
        return payload
    except:
        return None

def require_admin():
    """Require admin authentication"""
    user = get_user_from_token()
    if not user or user.get('role') != 'admin':
        return None
    return user

def require_head():
    """Require head authentication"""
    user = get_user_from_token()
    if not user or user.get('role') != 'head':
        return None
    return user

# ==================== ADMIN ENDPOINTS ====================

@messages_bp.route('/admin/send', methods=['POST'])
def admin_send_message():
    """Admin sends message to Head"""
    admin = require_admin()
    if not admin:
        return jsonify({'error': 'Admin authentication required'}), 401
    
    data = request.get_json()
    subject = data.get('subject', '').strip()
    message_content = data.get('message', '').strip()
    complaint_id = data.get('complaint_id')
    
    if not subject or not message_content:
        return jsonify({'error': 'Subject and message are required'}), 400
    
    if len(subject) > 200:
        return jsonify({'error': 'Subject too long (max 200 characters)'}), 400
    
    if len(message_content) > 5000:
        return jsonify({'error': 'Message too long (max 5000 characters)'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get head user ID (first head in system)
        cursor.execute("SELECT id FROM users WHERE role = 'head' AND is_active = 1 LIMIT 1")
        head = cursor.fetchone()
        
        if not head:
            return jsonify({'error': 'No active Head user found'}), 404
        
        head_id = head['id']
        
        # Validate complaint_id if provided
        if complaint_id:
            cursor.execute("SELECT id FROM complaints WHERE id = ?", (complaint_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Invalid complaint ID'}), 400
        
        # Insert message
        cursor.execute("""
            INSERT INTO admin_head_messages 
            (admin_id, head_id, subject, message_content, complaint_id, status)
            VALUES (?, ?, ?, ?, ?, 'unread')
        """, (admin['user_id'], head_id, subject, message_content, complaint_id))
        
        conn.commit()
        message_id = cursor.lastrowid
        
        logger.info(f"Admin {admin['user_id']} sent message {message_id} to Head {head_id}")
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': 'Message sent successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

@messages_bp.route('/admin/sent', methods=['GET'])
def admin_get_sent_messages():
    """Get all messages sent by admin"""
    admin = require_admin()
    if not admin:
        return jsonify({'error': 'Admin authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.id,
                m.subject,
                m.message_content,
                m.complaint_id,
                m.status,
                m.reply_content,
                m.replied_at,
                m.created_at,
                m.read_at,
                m.resolved_at,
                u.name as head_name,
                c.complaint_id as complaint_number
            FROM admin_head_messages m
            JOIN users u ON m.head_id = u.id
            LEFT JOIN complaints c ON m.complaint_id = c.id
            WHERE m.admin_id = ?
            ORDER BY m.created_at DESC
        """, (admin['user_id'],))
        
        messages = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'messages': messages,
            'total': len(messages)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching sent messages: {str(e)}")
        return jsonify({'error': 'Failed to fetch messages'}), 500

@messages_bp.route('/admin/<int:message_id>', methods=['GET'])
def admin_get_message_details(message_id):
    """Get specific message details"""
    admin = require_admin()
    if not admin:
        return jsonify({'error': 'Admin authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.*,
                u.name as head_name,
                c.complaint_id as complaint_number,
                c.description as complaint_description
            FROM admin_head_messages m
            JOIN users u ON m.head_id = u.id
            LEFT JOIN complaints c ON m.complaint_id = c.id
            WHERE m.id = ? AND m.admin_id = ?
        """, (message_id, admin['user_id']))
        
        message = cursor.fetchone()
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        return jsonify({
            'success': True,
            'message': dict(message)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching message details: {str(e)}")
        return jsonify({'error': 'Failed to fetch message'}), 500

# ==================== HEAD ENDPOINTS ====================

@messages_bp.route('/head/inbox', methods=['GET'])
def head_get_inbox():
    """Get all messages for Head"""
    head = require_head()
    if not head:
        return jsonify({'error': 'Head authentication required'}), 401
    
    status_filter = request.args.get('status')  # unread, read, resolved, all
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                m.id,
                m.subject,
                m.message_content,
                m.complaint_id,
                m.status,
                m.reply_content,
                m.replied_at,
                m.created_at,
                m.read_at,
                m.resolved_at,
                u.name as admin_name,
                u.email as admin_email,
                c.complaint_id as complaint_number
            FROM admin_head_messages m
            JOIN users u ON m.admin_id = u.id
            LEFT JOIN complaints c ON m.complaint_id = c.id
            WHERE m.head_id = ?
        """
        
        params = [head['user_id']]
        
        if status_filter and status_filter != 'all':
            query += " AND m.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY m.created_at DESC"
        
        cursor.execute(query, params)
        messages = [dict(row) for row in cursor.fetchall()]
        
        # Get counts
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'unread' THEN 1 ELSE 0 END) as unread,
                SUM(CASE WHEN status = 'read' THEN 1 ELSE 0 END) as read,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved
            FROM admin_head_messages
            WHERE head_id = ?
        """, (head['user_id'],))
        
        counts = dict(cursor.fetchone())
        
        return jsonify({
            'success': True,
            'messages': messages,
            'counts': counts
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching inbox: {str(e)}")
        return jsonify({'error': 'Failed to fetch messages'}), 500

@messages_bp.route('/head/<int:message_id>', methods=['GET'])
def head_get_message(message_id):
    """Get specific message and mark as read"""
    head = require_head()
    if not head:
        return jsonify({'error': 'Head authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get message
        cursor.execute("""
            SELECT 
                m.*,
                u.name as admin_name,
                u.email as admin_email,
                u.phone as admin_phone,
                c.complaint_id as complaint_number,
                c.description as complaint_description,
                c.status as complaint_status
            FROM admin_head_messages m
            JOIN users u ON m.admin_id = u.id
            LEFT JOIN complaints c ON m.complaint_id = c.id
            WHERE m.id = ? AND m.head_id = ?
        """, (message_id, head['user_id']))
        
        message = cursor.fetchone()
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        message_dict = dict(message)
        
        # Mark as read if unread
        if message_dict['status'] == 'unread':
            cursor.execute("""
                UPDATE admin_head_messages 
                SET status = 'read', read_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (message_id,))
            conn.commit()
            message_dict['status'] = 'read'
            message_dict['read_at'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': message_dict
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching message: {str(e)}")
        return jsonify({'error': 'Failed to fetch message'}), 500

@messages_bp.route('/head/<int:message_id>/reply', methods=['PUT'])
def head_reply_message(message_id):
    """Head replies to a message"""
    head = require_head()
    if not head:
        return jsonify({'error': 'Head authentication required'}), 401
    
    data = request.get_json()
    reply_content = data.get('reply', '').strip()
    
    if not reply_content:
        return jsonify({'error': 'Reply content is required'}), 400
    
    if len(reply_content) > 5000:
        return jsonify({'error': 'Reply too long (max 5000 characters)'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify message exists and belongs to this head
        cursor.execute("""
            SELECT id, status FROM admin_head_messages 
            WHERE id = ? AND head_id = ?
        """, (message_id, head['user_id']))
        
        message = cursor.fetchone()
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        # Update with reply
        cursor.execute("""
            UPDATE admin_head_messages 
            SET reply_content = ?, 
                replied_at = CURRENT_TIMESTAMP,
                status = CASE WHEN status = 'unread' THEN 'read' ELSE status END
            WHERE id = ?
        """, (reply_content, message_id))
        
        conn.commit()
        
        logger.info(f"Head replied to message {message_id}")
        
        return jsonify({
            'success': True,
            'message': 'Reply sent successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error replying to message: {str(e)}")
        return jsonify({'error': 'Failed to send reply'}), 500

@messages_bp.route('/head/<int:message_id>/resolve', methods=['PUT'])
def head_resolve_message(message_id):
    """Mark message as resolved"""
    head = require_head()
    if not head:
        return jsonify({'error': 'Head authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify message exists
        cursor.execute("""
            SELECT id FROM admin_head_messages 
            WHERE id = ? AND head_id = ?
        """, (message_id, head['user_id']))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Message not found'}), 404
        
        # Mark as resolved
        cursor.execute("""
            UPDATE admin_head_messages 
            SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (message_id,))
        
        conn.commit()
        
        logger.info(f"Head resolved message {message_id}")
        
        return jsonify({
            'success': True,
            'message': 'Message marked as resolved'
        }), 200
        
    except Exception as e:
        logger.error(f"Error resolving message: {str(e)}")
        return jsonify({'error': 'Failed to resolve message'}), 500

@messages_bp.route('/head/unread-count', methods=['GET'])
def head_get_unread_count():
    """Get count of unread messages"""
    head = require_head()
    if not head:
        return jsonify({'error': 'Head authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM admin_head_messages 
            WHERE head_id = ? AND status = 'unread'
        """, (head['user_id'],))
        
        result = cursor.fetchone()
        count = result['count'] if result else 0
        
        return jsonify({
            'success': True,
            'unread_count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'error': 'Failed to get count'}), 500
