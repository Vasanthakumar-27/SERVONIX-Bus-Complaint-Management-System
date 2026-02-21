"""Internal messaging system routes"""
from flask import Blueprint, request, jsonify
import logging

from ..database.connection import get_db
from ..auth.utils import get_user_by_token

logger = logging.getLogger(__name__)

messaging_bp = Blueprint('messaging', __name__, url_prefix='/api/messages')


@messaging_bp.route('/send', methods=['POST'])
def send_message():
    """Send a message from head to admin or admin to head"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['head', 'admin']:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.json
    recipient_id = data.get('receiver_id') or data.get('recipient_id')
    recipient_email = data.get('recipient_email')
    subject = data.get('subject', '').strip()
    body = data.get('body', '') or data.get('message', '')
    body = body.strip() if body else ''
    
    if not body:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # If email provided instead of ID, look up the user ID
        if not recipient_id and recipient_email:
            cursor.execute('SELECT id, role FROM users WHERE email = ?', (recipient_email,))
            receiver = cursor.fetchone()
            if not receiver:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Recipient not found'}), 404
            recipient_id = receiver['id']
        elif not recipient_id:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Recipient email or ID is required'}), 400
        else:
            # Verify receiver exists
            cursor.execute('SELECT id, role FROM users WHERE id = ?', (recipient_id,))
            receiver = cursor.fetchone()
            if not receiver:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Recipient not found'}), 404
        
        # Insert message - using correct schema column names (receiver_id, body)
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, subject, body, created_at)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (user['id'], recipient_id, subject, body))
        
        message_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User {user['id']} sent message {message_id} to user {recipient_id}")
        return jsonify({
            'message': 'Message sent successfully',
            'id': message_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': str(e)}), 500


@messaging_bp.route('/inbox', methods=['GET'])
def get_inbox():
    """Get messages for current user"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['head', 'admin']:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT m.id, m.sender_id, m.receiver_id as recipient_id, m.subject, m.body as message,
                   m.is_read, m.created_at, m.read_at,
                   u.name as sender_name, u.email as sender_email, u.role as sender_role
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.receiver_id = ?
            ORDER BY m.created_at DESC
        ''', (user['id'],))
        
        messages = [dict(row) for row in cursor.fetchall()]
        
        # Get unread count
        cursor.execute('SELECT COUNT(*) as unread FROM messages WHERE receiver_id = ? AND is_read = 0', (user['id'],))
        unread_count = cursor.fetchone()['unread']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'messages': messages,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching inbox: {str(e)}")
        return jsonify({'error': str(e)}), 500


@messaging_bp.route('/sent', methods=['GET'])
def get_sent_messages():
    """Get sent messages for current user"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['head', 'admin']:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT m.id, m.sender_id, m.receiver_id as recipient_id, m.subject, m.body as message,
                   m.is_read, m.created_at, m.read_at,
                   u.name as recipient_name, u.email as recipient_email, u.role as recipient_role
            FROM messages m
            JOIN users u ON u.id = m.receiver_id
            WHERE m.sender_id = ?
            ORDER BY m.created_at DESC
        ''', (user['id'],))
        
        messages = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'messages': messages}), 200
        
    except Exception as e:
        logger.error(f"Error fetching sent messages: {str(e)}")
        return jsonify({'error': str(e)}), 500


@messaging_bp.route('/<int:message_id>/read', methods=['PUT'])
def mark_message_read(message_id):
    """Mark a message as read"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify message belongs to user (using receiver_id)
        cursor.execute('SELECT receiver_id FROM messages WHERE id = ?', (message_id,))
        message = cursor.fetchone()
        if not message or message['receiver_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Message not found'}), 404
        
        cursor.execute('''
            UPDATE messages 
            SET is_read = 1, read_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (message_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Message marked as read'}), 200
        
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}")
        return jsonify({'error': str(e)}), 500


@messaging_bp.route('/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    """Delete a message (sender or recipient can delete)"""
    user = get_user_by_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] not in ['head', 'admin']:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify user owns the message (sender or receiver)
        cursor.execute('''
            SELECT sender_id, receiver_id 
            FROM messages 
            WHERE id = ?
        ''', (message_id,))
        message = cursor.fetchone()
        
        if not message:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Message not found'}), 404
        
        if message['sender_id'] != user['id'] and message['receiver_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'You can only delete your own messages'}), 403
        
        cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User {user['id']} deleted message {message_id}")
        return jsonify({'message': 'Message deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        return jsonify({'error': str(e)}), 500
