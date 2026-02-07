"""Feedback system routes"""
from flask import Blueprint, request, jsonify
import logging

from database.connection import get_db
from utils.decorators import require_user_auth, require_head_auth, require_admin_auth

logger = logging.getLogger(__name__)

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api')


@feedback_bp.route('/feedback', methods=['GET', 'POST'])
def feedback_endpoint():
    """GET: Fetch all feedback (head only), POST: Submit feedback (user)"""
    if request.method == 'GET':
        # Get all feedback - head only
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'head auth required'}), 401
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Use actual table columns - feedback has user_name, user_email directly
            cursor.execute('''
                SELECT f.id, f.user_id, f.user_name, f.user_email, f.rating, f.message, 
                       f.status, f.reviewed_by, f.reviewed_at, f.created_at, f.updated_at,
                       f.complaint_id
                FROM feedback f
                ORDER BY f.created_at DESC
            ''')
            
            feedback_list = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return jsonify({'feedback': feedback_list}), 200
            
        except Exception as e:
            logger.error(f"Error fetching all feedback: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    else:  # POST
        # Submit feedback with rating and message
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        # Validate required fields
        if not data.get('rating') or not data.get('message'):
            return jsonify({'error': 'Rating and message are required'}), 400
        
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        message = data['message'].strip()
        if len(message) < 1:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # feedback table has: user_id, user_name, user_email, rating, message, status
            cursor.execute('''
                INSERT INTO feedback (user_id, user_name, user_email, rating, message, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', datetime('now', 'localtime'))
            ''', (user['id'], user.get('name', 'Unknown'), user.get('email', ''), rating, message))
            
            feedback_id = cursor.lastrowid
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"User {user['id']} submitted feedback {feedback_id} with rating {rating}")
            return jsonify({'id': feedback_id, 'message': 'Feedback sent successfully to head administrator'}), 201
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            return jsonify({'error': str(e)}), 500


@feedback_bp.route('/my/feedback', methods=['GET'])
def get_my_feedback():
    """Get authenticated user's feedback history"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, rating, message, status, created_at, reviewed_at
            FROM feedback
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user['id'],))
        
        feedback_list = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return jsonify({'feedback': feedback_list}), 200
        
    except Exception as e:
        logger.error(f"Error fetching user feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500


@feedback_bp.route('/my/feedback/<int:feedback_id>', methods=['DELETE'])
def delete_my_feedback(feedback_id):
    """Allow users to delete their own feedback"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if feedback exists and belongs to user
        cursor.execute('SELECT id, user_id FROM feedback WHERE id = ?', (feedback_id,))
        feedback = cursor.fetchone()
        
        if not feedback:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Feedback not found'}), 404
        
        if feedback['user_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'You can only delete your own feedback'}), 403
        
        # Delete the feedback
        cursor.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User {user['id']} deleted feedback {feedback_id}")
        return jsonify({'message': 'Feedback deleted successfully. You can submit new feedback.'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500


@feedback_bp.route('/head/all-feedback', methods=['GET'])
@feedback_bp.route('/head/feedback', methods=['GET'])
def get_all_feedback():
    """Head admin: Get all feedback with filters"""
    user = require_head_auth()
    if not user:
        return jsonify({'error': 'head auth required'}), 401
    
    status = request.args.get('status')
    rating = request.args.get('rating')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Use actual table columns - feedback table has user_name, user_email directly
        query = '''
            SELECT f.id, f.user_id, f.user_name, f.user_email, f.rating, f.message,
                   f.status, f.reviewed_by, f.reviewed_at, f.created_at, f.updated_at,
                   f.complaint_id
            FROM feedback f
            WHERE 1=1
        '''
        params = []
        
        if status:
            query += ' AND f.status = ?'
            params.append(status)
        
        if rating:
            query += ' AND f.rating = ?'
            params.append(int(rating))
        
        query += ' ORDER BY f.created_at DESC LIMIT 200'
        
        cursor.execute(query, params)
        feedback_list = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'feedback': feedback_list}), 200
        
    except Exception as e:
        logger.error(f"Error fetching all feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500


@feedback_bp.route('/head/feedback/<int:feedback_id>', methods=['PUT'])
def update_feedback_status(feedback_id):
    """Head admin: Update feedback status"""
    user = require_head_auth()
    if not user:
        return jsonify({'error': 'head auth required'}), 401
    
    data = request.get_json() or {}
    status = data.get('status')
    
    if status not in ['pending', 'reviewed', 'archived']:
        return jsonify({'error': 'Invalid status'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Map 'archived' to 'responded' since schema uses (pending, reviewed, responded)
        if status == 'archived':
            status = 'responded'
        
        cursor.execute('''
            UPDATE feedback
            SET status = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (status, feedback_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Feedback not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Head {user['id']} updated feedback {feedback_id} to {status}")
        return jsonify({'message': 'Feedback status updated'}), 200
        
    except Exception as e:
        logger.error(f"Error updating feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500


@feedback_bp.route('/head/feedback/<int:feedback_id>', methods=['DELETE'])
@feedback_bp.route('/feedback/<int:feedback_id>', methods=['DELETE'])
def delete_feedback(feedback_id):
    """Head admin: Delete feedback"""
    user = require_head_auth()
    if not user:
        return jsonify({'error': 'head auth required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Feedback not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Head {user['id']} deleted feedback {feedback_id}")
        return jsonify({'message': 'Feedback deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500


@feedback_bp.route('/admin/feedback', methods=['GET'])
def admin_get_feedback():
    """Admin: Get feedback for viewing"""
    user = require_admin_auth()
    if not user:
        return jsonify({'error': 'admin auth required'}), 401
    
    status = request.args.get('status')
    rating = request.args.get('rating')
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all feedback (admins can view all feedback)
        query = '''
            SELECT f.*, u.name as reviewer_name
            FROM feedback f
            LEFT JOIN users u ON f.reviewed_by = u.id
            WHERE 1=1
        '''
        params = []
        
        if status:
            query += ' AND f.status = ?'
            params.append(status)
        
        if rating:
            query += ' AND f.rating = ?'
            params.append(int(rating))
        
        query += ' ORDER BY f.created_at DESC LIMIT 100'
        
        cursor.execute(query, params)
        feedback_list = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify(feedback_list), 200
        
    except Exception as e:
        logger.error(f"Error fetching feedback for admin: {str(e)}")
        return jsonify({'error': str(e)}), 500


@feedback_bp.route('/head/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """Head admin: Get feedback statistics"""
    user = require_head_auth()
    if not user:
        return jsonify({'error': 'head auth required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('SELECT COUNT(*) as total FROM feedback')
        total = cursor.fetchone()['total']
        
        # By status
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM feedback
            GROUP BY status
        ''')
        by_status = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # By rating
        cursor.execute('''
            SELECT rating, COUNT(*) as count
            FROM feedback
            GROUP BY rating
            ORDER BY rating DESC
        ''')
        by_rating = {row['rating']: row['count'] for row in cursor.fetchall()}
        
        # Average rating
        cursor.execute('SELECT AVG(rating) as avg_rating FROM feedback')
        avg_rating = cursor.fetchone()['avg_rating'] or 0
        
        # Recent feedback count (last 7 days)
        cursor.execute('''
            SELECT COUNT(*) as recent
            FROM feedback
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        recent = cursor.fetchone()['recent']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total': total,
            'by_status': by_status,
            'by_rating': by_rating,
            'average_rating': round(avg_rating, 2),
            'recent_count': recent
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching feedback stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
