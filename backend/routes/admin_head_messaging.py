"""Admin-to-Head Professional Communication System"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

from ..database.connection import get_db
from ..auth.utils import get_user_by_token
from ..utils.helpers import format_datetime_for_db

logger = logging.getLogger(__name__)

admin_head_bp = Blueprint('admin_head', __name__, url_prefix='/api/admin-head')


@admin_head_bp.route('/messages/send', methods=['POST'])
def send_admin_head_message():
    """Admin sends message to Head with optional complaint escalation"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['admin', 'head']:
        return jsonify({'error': 'Unauthorized. Admin or Head access required'}), 401
    
    data = request.json
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()
    complaint_id = data.get('complaint_id')  # Optional escalation
    priority = data.get('priority', 'normal')  # low, normal, high, urgent
    
    if not subject:
        return jsonify({'error': 'Subject is required'}), 400
    if not message:
        return jsonify({'error': 'Message content is required'}), 400
    
    if priority not in ['low', 'normal', 'high', 'urgent']:
        priority = 'normal'
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get Head user ID (there should be only one head)
        if user['role'] == 'admin':
            # Admin sending to Head
            cursor.execute('SELECT id FROM users WHERE role = ? AND is_active = 1 LIMIT 1', ('head',))
            head = cursor.fetchone()
            if not head:
                cursor.close()
                conn.close()
                return jsonify({'error': 'No active Head found'}), 404
            receiver_id = head['id']
        else:
            # Head replying - need recipient_id in request
            receiver_id = data.get('receiver_id')
            if not receiver_id:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Receiver ID required for Head replies'}), 400
        
        # Verify complaint exists if provided
        if complaint_id:
            cursor.execute('SELECT id, description FROM complaints WHERE id = ?', (complaint_id,))
            complaint = cursor.fetchone()
            if not complaint:
                cursor.close()
                conn.close()
                return jsonify({'error': f'Complaint #{complaint_id} not found'}), 404
        
        # Insert message with escalation tracking
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, subject, body, 
                                 is_read, created_at, complaint_id, priority)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?)
        ''', (user['id'], receiver_id, subject, message, 
              format_datetime_for_db(), complaint_id, priority))
        
        message_id = cursor.lastrowid
        
        # Update complaint status when escalated to head
        if complaint_id:
            cursor.execute('''
                UPDATE complaints 
                SET updated_at = ?
                WHERE id = ?
            ''', (format_datetime_for_db(), complaint_id))
        
        conn.commit()
        
        # Get complete message details for response
        cursor.execute('''
            SELECT m.*, u.name as sender_name, r.name as receiver_name
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            JOIN users r ON r.id = m.receiver_id
            WHERE m.id = ?
        ''', (message_id,))
        
        created_message = dict(cursor.fetchone())
        
        cursor.close()
        conn.close()
        
        logger.info(f"{user['role'].upper()} {user['id']} sent message {message_id} to {receiver_id}" +
                   (f" (escalated complaint #{complaint_id})" if complaint_id else ""))
        
        # Emit real-time notification
        try:
            from flask import current_app
            if hasattr(current_app, 'socketio'):
                current_app.socketio.emit('new_admin_head_message', {
                    'message_id': message_id,
                    'receiver_id': receiver_id,
                    'sender_name': user['name'],
                    'subject': subject,
                    'priority': priority,
                    'complaint_id': complaint_id,
                    'timestamp': created_message['created_at']
                }, room=f'user_{receiver_id}')
        except Exception as e:
            logger.warning(f"Failed to emit real-time notification: {e}")
        
        return jsonify({
            'message': 'Message sent successfully',
            'id': message_id,
            'escalated': complaint_id is not None,
            'data': created_message
        }), 201
        
    except Exception as e:
        logger.error(f"Error sending admin-head message: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to send message: {str(e)}'}), 500


@admin_head_bp.route('/messages/inbox', methods=['GET'])
def get_admin_head_inbox():
    """Get all messages for current user (Admin or Head)"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['admin', 'head']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    filter_status = request.args.get('status', 'all')  # all, unread, read, resolved
    filter_priority = request.args.get('priority')  # low, normal, high, urgent
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get received messages
        query = '''
            SELECT m.id, m.sender_id, m.receiver_id, m.subject, m.body as message,
                   m.is_read, m.read_at, m.created_at, m.complaint_id, m.priority,
                   m.resolved, m.resolved_at, m.resolution_notes,
                   sender.name as sender_name, sender.email as sender_email, sender.role as sender_role,
                   c.description as complaint_description, c.status as complaint_status
            FROM messages m
            JOIN users sender ON sender.id = m.sender_id
            LEFT JOIN complaints c ON c.id = m.complaint_id
            WHERE m.receiver_id = ?
        '''
        
        params = [user['id']]
        
        if filter_status == 'unread':
            query += ' AND m.is_read = 0'
        elif filter_status == 'read':
            query += ' AND m.is_read = 1 AND (m.resolved IS NULL OR m.resolved = 0)'
        elif filter_status == 'resolved':
            query += ' AND m.resolved = 1'
        
        if filter_priority:
            query += ' AND m.priority = ?'
            params.append(filter_priority)
        
        query += ' ORDER BY m.priority DESC, m.created_at DESC'
        
        cursor.execute(query, params)
        received = [dict(row) for row in cursor.fetchall()]
        
        # Get sent messages
        cursor.execute('''
            SELECT m.id, m.sender_id, m.receiver_id, m.subject, m.body as message,
                   m.is_read, m.read_at, m.created_at, m.complaint_id, m.priority,
                   m.resolved, m.resolved_at, m.resolution_notes,
                   receiver.name as receiver_name, receiver.email as receiver_email, receiver.role as receiver_role,
                   c.description as complaint_description, c.status as complaint_status
            FROM messages m
            JOIN users receiver ON receiver.id = m.receiver_id
            LEFT JOIN complaints c ON c.id = m.complaint_id
            WHERE m.sender_id = ?
            ORDER BY m.created_at DESC
        ''', (user['id'],))
        
        sent = [dict(row) for row in cursor.fetchall()]
        
        # Count unread
        cursor.execute('SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0', (user['id'],))
        unread_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'received': received,
            'sent': sent,
            'unread_count': unread_count,
            'user_role': user['role']
        })
        
    except Exception as e:
        logger.error(f"Error fetching inbox: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_head_bp.route('/messages/<int:message_id>/read', methods=['PUT'])
def mark_message_read(message_id):
    """Mark message as read"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['admin', 'head']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify message ownership
        cursor.execute('SELECT id, receiver_id, is_read FROM messages WHERE id = ?', (message_id,))
        message = cursor.fetchone()
        
        if not message:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Message not found'}), 404
        
        if message['receiver_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Mark as read
        cursor.execute('''
            UPDATE messages 
            SET is_read = 1, read_at = ?
            WHERE id = ?
        ''', (format_datetime_for_db(), message_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Marked as read'}), 200
        
    except Exception as e:
        logger.error(f"Error marking message read: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_head_bp.route('/messages/<int:message_id>/resolve', methods=['PUT'])
def resolve_message(message_id):
    """Head marks message as resolved with notes"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] != 'head':
        return jsonify({'error': 'Only Head can resolve messages'}), 403
    
    data = request.json or {}
    resolution_notes = data.get('resolution_notes', '').strip()
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify message exists and user is receiver
        cursor.execute('SELECT id, receiver_id, sender_id FROM messages WHERE id = ?', (message_id,))
        message = cursor.fetchone()
        
        if not message:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Message not found'}), 404
        
        if message['receiver_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Mark as resolved
        cursor.execute('''
            UPDATE messages 
            SET resolved = 1, 
                resolved_at = ?,
                resolution_notes = ?,
                is_read = 1,
                read_at = COALESCE(read_at, ?)
            WHERE id = ?
        ''', (format_datetime_for_db(), resolution_notes, format_datetime_for_db(), message_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Notify sender
        try:
            from flask import current_app
            if hasattr(current_app, 'socketio'):
                current_app.socketio.emit('message_resolved', {
                    'message_id': message_id,
                    'resolved_by': user['name'],
                    'timestamp': format_datetime_for_db()
                }, room=f'user_{message["sender_id"]}')
        except Exception as e:
            logger.warning(f"Failed to emit resolution notification: {e}")
        
        return jsonify({'message': 'Message resolved successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error resolving message: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_head_bp.route('/messages/<int:message_id>/reply', methods=['POST'])
def reply_to_message(message_id):
    """Reply to a message (creates new message in thread)"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['admin', 'head']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    reply_message = data.get('message', '').strip()
    
    if not reply_message:
        return jsonify({'error': 'Reply message is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get original message
        cursor.execute('''
            SELECT id, sender_id, receiver_id, subject, complaint_id, priority
            FROM messages WHERE id = ?
        ''', (message_id,))
        original = cursor.fetchone()
        
        if not original:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Original message not found'}), 404
        
        # Determine reply recipient (sender of original message)
        reply_to_id = original['sender_id'] if original['receiver_id'] == user['id'] else original['receiver_id']
        
        # Create reply subject
        reply_subject = original['subject']
        if not reply_subject.startswith('Re: '):
            reply_subject = f"Re: {reply_subject}"
        
        # Insert reply
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, subject, body,
                                 is_read, created_at, complaint_id, priority, parent_message_id)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
        ''', (user['id'], reply_to_id, reply_subject, reply_message,
              format_datetime_for_db(), original['complaint_id'], 
              original['priority'], message_id))
        
        reply_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        # Real-time notification
        try:
            from flask import current_app
            if hasattr(current_app, 'socketio'):
                current_app.socketio.emit('new_admin_head_message', {
                    'message_id': reply_id,
                    'receiver_id': reply_to_id,
                    'sender_name': user['name'],
                    'subject': reply_subject,
                    'is_reply': True,
                    'parent_id': message_id,
                    'timestamp': format_datetime_for_db()
                }, room=f'user_{reply_to_id}')
        except Exception as e:
            logger.warning(f"Failed to emit reply notification: {e}")
        
        return jsonify({
            'message': 'Reply sent successfully',
            'id': reply_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error sending reply: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_head_bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """Get unread message count for current user"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['admin', 'head']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as count,
                   SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent_count
            FROM messages 
            WHERE receiver_id = ? AND is_read = 0
        ''', (user['id'],))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'total': result['count'],
            'urgent': result['urgent_count']
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'error': str(e)}), 500
