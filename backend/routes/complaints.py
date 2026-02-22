"""Complaint management routes - With auto-assignment and notifications"""
from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
import logging
import os
import uuid
import tempfile
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

from ..database.connection import get_db
from ..utils.decorators import require_user_auth, require_admin_auth, require_head_auth
from ..utils.helpers import format_datetime_for_db, get_file_mime_type, allowed_file
from ..config import config
from ..pdf_generator import generate_complaints_pdf, generate_complaint_detail_pdf

logger = logging.getLogger(__name__)

complaints_bp = Blueprint('complaints', __name__, url_prefix='/api')


def emit_complaints_update():
    """Emit real-time complaint update via SocketIO"""
    try:
        from flask import current_app
        if hasattr(current_app, 'socketio'):
            current_app.socketio.emit('complaints_updated', {'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Failed to emit complaints update: {e}")


def get_notification_service():
    """Get the notification service from app context"""
    try:
        from flask import current_app
        return current_app.config.get('notification_service')
    except Exception:
        return None


def get_media_files_for_complaint(cursor, complaint_id):
    """Get all media files associated with a complaint from complaint_media table"""
    try:
        cursor.execute("""
            SELECT id, file_name, file_path, mime_type, file_size
            FROM complaint_media
            WHERE complaint_id = ?
        """, (complaint_id,))
        media_files = []
        for row in cursor.fetchall():
            media = dict(row)
            # Construct full URL for media file
            media['url'] = f"/api/uploads/{media['file_path']}"
            media_files.append(media)
        return media_files
    except Exception as e:
        logger.error(f"Error getting media files for complaint {complaint_id}: {e}")
        return []


def enrich_complaints_with_media(cursor, complaints):
    """Add media_files list to each complaint"""
    for complaint in complaints:
        complaint['media_files'] = get_media_files_for_complaint(cursor, complaint['id'])
    return complaints


@complaints_bp.route('/complaints', methods=['POST'])
def create_complaint():
    """Create a new complaint with auto-assignment and notifications"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Handle file upload (multipart/form-data) or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
            proof_file = request.files.get('proof')
            
            media_path = None
            if proof_file and proof_file.filename:
                uploads_dir = config.UPLOAD_FOLDER
                os.makedirs(uploads_dir, exist_ok=True)
                
                filename = secure_filename(proof_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(uploads_dir, unique_filename)
                
                proof_file.save(file_path)
                media_path = unique_filename
        else:
            data = request.get_json() or {}
            media_path = None
        
        # Validate required fields - using schema columns
        if not data.get('description'):
            return jsonify({'error': 'Description is required'}), 400
        
        # Map frontend field names to schema field names
        complaint_type = data.get('category') or data.get('complaint_type') or 'general'
        bus_number = data.get('bus_number', '')
        route_number = data.get('route_name') or data.get('route_number', '')
        from_location = data.get('from_location', '')
        to_location = data.get('to_location', '')
        incident_time = data.get('incident_time')
        
        # Auto-assign to admin based on route/district
        assigned_admin_id = None
        assigned_district_id = None
        assignment_reason = None
        try:
            from ..services.auto_assignment import AutoAssignmentService
            assignment = AutoAssignmentService.find_admin_for_complaint(route_number, bus_number)
            if assignment:
                assigned_admin_id = assignment['admin_id']
                assigned_district_id = assignment.get('district_id')
                assignment_reason = assignment['reason']
                logger.info(f"Auto-assignment: {assignment_reason}")
        except Exception as ae:
            logger.warning(f"Auto-assignment failed, complaint will be unassigned: {ae}")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get user's name and email from the user object
        user_name = user.get('name', 'Unknown User')
        user_email = user.get('email', '')
        
        current_time = format_datetime_for_db()
        cursor.execute("""
            INSERT INTO complaints (user_id, name, email, category, description, route, 
                                   bus_number, status, assigned_to, district_id, proof_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """, (user['id'], user_name, user_email, complaint_type, data['description'], route_number,
              bus_number, assigned_admin_id, assigned_district_id, media_path, current_time))
        
        complaint_id = cursor.lastrowid
        
        # Link media files to complaint if media_ids were provided
        # Copy file info from media_files to complaint_media
        media_ids = data.get('media_ids', [])
        if media_ids:
            for media_id in media_ids:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO complaint_media (complaint_id, media_id, created_at)
                        VALUES (?, ?, ?)
                    """, (complaint_id, media_id, current_time))
                except Exception as media_err:
                    logger.warning(f"Failed to link media {media_id} to complaint {complaint_id}: {media_err}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        emit_complaints_update()
        
        # Send notifications
        notification_service = get_notification_service()
        if notification_service:
            try:
                # Notify all admins about new complaint
                notification_service.notify_complaint_created(
                    complaint_id=complaint_id,
                    user_name=user.get('name', 'User'),
                    complaint_type=complaint_type,
                    route_number=route_number
                )
                
                # If auto-assigned, notify the specific admin
                if assigned_admin_id:
                    notification_service.notify_complaint_assigned(
                        complaint_id=complaint_id,
                        admin_id=assigned_admin_id,
                        complaint_type=complaint_type
                    )
            except Exception as ne:
                logger.warning(f"Notification send failed: {ne}")
        
        # Emit real-time Socket.IO event
        try:
            socketio_service = current_app.config.get('socketio_service')
            if socketio_service:
                socketio_service.emit_complaint_update('created', complaint_id)
                if assigned_admin_id:
                    socketio_service.emit_complaint_assigned(complaint_id, assigned_admin_id)
        except Exception as se:
            logger.warning(f"Socket.IO emit failed: {se}")
        
        logger.info(f"Created complaint {complaint_id} for user {user['id']}, assigned to admin {assigned_admin_id}")
        return jsonify({
            'id': complaint_id,
            'message': 'Complaint submitted successfully',
            'assigned_to': assigned_admin_id,
            'assignment_reason': assignment_reason
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating complaint: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to create complaint: {str(e)}'}), 500


@complaints_bp.route('/complaints', methods=['GET'])
@complaints_bp.route('/admin/complaints', methods=['GET'])
def list_complaints():
    """List complaints (admin/head only) with filters.
    
    STRICT FILTERING:
    - Head admin (role='head'): Can see ALL complaints
    - Regular admin (role='admin'): Can ONLY see complaints assigned to them (assigned_to = admin.id)
    """
    user = require_admin_auth()
    if not user:
        return jsonify({'error': 'admin auth required'}), 401
    
    status = request.args.get('status')
    q = request.args.get('q')
    show_unassigned = request.args.get('unassigned', 'false').lower() == 'true'
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        base = """
            SELECT c.*, u.name as user_name, u.email as user_email,
                   a.name as admin_name
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.id
            LEFT JOIN users a ON c.assigned_to = a.id
        """
        
        conds = []
        vals = []
        
        # ===== STRICT ASSIGNMENT FILTERING =====
        # Regular admins ONLY see complaints assigned to them
        # Head admins can see all complaints (including unassigned)
        if user.get('role') == 'admin':
            conds.append('c.assigned_to = ?')
            vals.append(user['id'])
        elif user.get('role') == 'head' and show_unassigned:
            # Head admin can request to see only unassigned complaints
            conds.append('c.assigned_to IS NULL')
        # If head admin without unassigned filter, show all complaints
        
        if status:
            conds.append('c.status=?')
            vals.append(status)
        
        if q:
            conds.append('(c.description LIKE ? OR c.complaint_type LIKE ? OR c.bus_number LIKE ?)')
            vals.extend(['%' + q + '%'] * 3)
        
        if conds:
            base += ' WHERE ' + ' AND '.join(conds)
        base += ' ORDER BY c.created_at DESC'
        
        cursor.execute(base, vals)
        rows = cursor.fetchall()
        
        complaints = [dict(row) for row in rows]
        
        # Enrich with media files
        complaints = enrich_complaints_with_media(cursor, complaints)
        
        return jsonify({'complaints': complaints})
    except Exception as e:
        logger.error(f"Error listing complaints: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch complaints', 'detail': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@complaints_bp.route('/user/complaints', methods=['GET'])
def list_user_complaints():
    """List complaints for authenticated user"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'auth required'}), 401
    
    status = request.args.get('status')
    search = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    conn = get_db()
    cursor = conn.cursor()
    
    base_query = """
        SELECT c.*, a.name as admin_name
        FROM complaints c
        LEFT JOIN users a ON c.assigned_to = a.id
        WHERE c.user_id = ?
    """
    
    conditions = []
    params = [user['id']]
    
    if status:
        conditions.append('c.status = ?')
        params.append(status)
    
    if search:
        conditions.append('(c.description LIKE ? OR c.bus_number LIKE ? OR c.complaint_type LIKE ?)')
        search_term = f'%{search}%'
        params.extend([search_term] * 3)
    
    if conditions:
        base_query += ' AND ' + ' AND '.join(conditions)
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM complaints c WHERE c.user_id = ?"
    count_params = [user['id']]
    if status:
        count_query += ' AND c.status = ?'
        count_params.append(status)
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
    
    # Add pagination
    base_query += ' ORDER BY c.created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    
    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    
    complaints = []
    for row in rows:
        complaint = dict(row)
        
        # Check if edit allowed (within 5 minutes)
        if complaint.get('created_at'):
            try:
                created_at = datetime.strptime(complaint['created_at'], '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                time_diff = now - created_at
                complaint['edit_allowed'] = time_diff <= timedelta(minutes=5)
            except (ValueError, TypeError):
                complaint['edit_allowed'] = False
        else:
            complaint['edit_allowed'] = False
        
        # Add media files
        complaint['media_files'] = get_media_files_for_complaint(cursor, complaint['id'])
        
        complaints.append(complaint)
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'complaints': complaints,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@complaints_bp.route('/complaints/<int:complaint_id>', methods=['GET'])
def get_complaint_detail(complaint_id):
    """Get single complaint details"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'auth required'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, u.name as user_name, u.email as user_email,
               a.name as admin_name
        FROM complaints c
        LEFT JOIN users u ON c.user_id = u.id
        LEFT JOIN users a ON c.assigned_to = a.id
        WHERE c.id = ?
    """, (complaint_id,))
    
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({'error': 'not found'}), 404
    
    complaint = dict(row)
    
    # Check permission (owner or admin/head)
    if complaint['user_id'] != user['id'] and user['role'] not in ['admin', 'head']:
        cursor.close()
        conn.close()
        return jsonify({'error': 'unauthorized'}), 403
    
    # Add media files
    complaint['media_files'] = get_media_files_for_complaint(cursor, complaint_id)
    
    cursor.close()
    conn.close()
    return jsonify(complaint)


@complaints_bp.route('/complaints/<int:complaint_id>/status', methods=['PUT'])
def update_complaint_status(complaint_id):
    """Update complaint status only (admin/head shortcut endpoint)"""
    user = require_admin_auth()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        data = request.get_json() or {}
        new_status = data.get('status', '').strip()
        valid_statuses = ('pending', 'in-progress', 'resolved', 'rejected')
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, assigned_to, status FROM complaints WHERE id = ?', (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404
        # Regular admins can only update their assigned complaints
        if user['role'] == 'admin' and complaint['assigned_to'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Not authorized to update this complaint'}), 403
        resolved_at = "datetime('now')" if new_status == 'resolved' else 'NULL'
        cursor.execute(f'''
            UPDATE complaints SET status = ?, updated_at = datetime('now'),
            resolved_at = {resolved_at} WHERE id = ?
        ''', (new_status, complaint_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Status updated', 'status': new_status}), 200
    except Exception as e:
        logger.error(f"Error updating complaint status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@complaints_bp.route('/my/complaints', methods=['GET'])
def list_my_complaints():
    """List my complaints (legacy endpoint)"""
    return list_user_complaints()


@complaints_bp.route('/my/complaints/<int:complaint_id>', methods=['DELETE'])
def delete_my_complaint(complaint_id):
    """Delete my complaint"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'auth required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify ownership
        cursor.execute(
            'SELECT id, user_id, category, status FROM complaints WHERE id = ?',
            (complaint_id,)
        )
        complaint = cursor.fetchone()
        
        if not complaint:
            return jsonify({
                'success': False,
                'error': 'Complaint not found'
            }), 404
        
        if complaint['user_id'] != user['id']:
            return jsonify({
                'success': False,
                'error': 'You can only delete your own complaints'
            }), 403
        
        # Delete complaint
        cursor.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
        conn.commit()
        
        logger.info(f"User {user['name']} (ID: {user['id']}) deleted their complaint #{complaint_id}")
        
        emit_complaints_update()
        
        return jsonify({
            'success': True,
            'message': 'Complaint deleted successfully',
            'deleted_id': complaint_id
        }), 200
    
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error deleting complaint #{complaint_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Database error occurred'
        }), 500
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting complaint #{complaint_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete complaint'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@complaints_bp.route('/complaints/<int:complaint_id>', methods=['PUT'])
def update_complaint(complaint_id):
    """Update complaint (admin/head or owner within 5 minutes)"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'auth required'}), 401
        
        data = request.get_json() or {}
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get complaint
        cursor.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,))
        complaint = cursor.fetchone()
        
        if not complaint:
            cursor.close()
            conn.close()
            return jsonify({'error': 'not found'}), 404
        
        # Check permissions
        is_admin = user['role'] in ['admin', 'head']
        is_owner = complaint['user_id'] == user['id']
        
        if is_owner and not is_admin:
            # Check 5-minute edit window
            try:
                created_at = datetime.strptime(complaint['created_at'], '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                if (now - created_at) > timedelta(minutes=5):
                    cursor.close()
                    conn.close()
                    return jsonify({'error': 'edit window expired'}), 403
            except (ValueError, TypeError):
                cursor.close()
                conn.close()
                return jsonify({'error': 'invalid timestamp format'}), 400
        
        if not is_admin and not is_owner:
            cursor.close()
            conn.close()
            return jsonify({'error': 'unauthorized'}), 403
        
        # Update fields
        updates = []
        params = []
        old_status = complaint['status']
        new_status = None
        
        if 'status' in data and is_admin:
            updates.append('status = ?')
            params.append(data['status'])
            new_status = data['status']
        
        if 'admin_response' in data and is_admin:
            updates.append('admin_response = ?')
            params.append(data['admin_response'])
        
        if 'assigned_to' in data and is_admin:
            updates.append('assigned_to = ?')
            params.append(data['assigned_to'])
        
        if 'description' in data:
            updates.append('description = ?')
            params.append(data['description'])
        
        if 'complaint_type' in data:
            updates.append('category = ?')
            params.append(data['complaint_type'])
        
        if 'category' in data:
            updates.append('category = ?')
            params.append(data['category'])
        
        if updates:
            updates.append('updated_at = ?')
            params.append(format_datetime_for_db())
            
            query = f"UPDATE complaints SET {', '.join(updates)} WHERE id = ?"
            params.append(complaint_id)
            cursor.execute(query, params)
            conn.commit()
            
            # Get updated complaint for notifications
            cursor.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,))
            updated_complaint = cursor.fetchone()
        else:
            updated_complaint = complaint
        
        cursor.close()
        conn.close()
        
        emit_complaints_update()
        
        # Send notifications for status change or admin response
        notification_service = get_notification_service()
        if notification_service and updated_complaint:
            try:
                # Notify user of status change
                if new_status and new_status != old_status:
                    notification_service.notify_complaint_status_change(
                        complaint_id=complaint_id,
                        user_id=updated_complaint['user_id'],
                        new_status=new_status,
                        admin_name=user.get('name')
                    )
                
                # Notify user of admin response
                if 'admin_response' in data and data['admin_response']:
                    notification_service.notify_complaint_response(
                        complaint_id=complaint_id,
                        user_id=updated_complaint['user_id'],
                        admin_name=user.get('name', 'Admin')
                    )
            except Exception as ne:
                logger.warning(f"Notification send failed: {ne}")
        
        return jsonify({'message': 'updated'}), 200
    
    except Exception as e:
        logger.error(f"Error updating complaint: {e}")
        return jsonify({'error': str(e)}), 500


@complaints_bp.route('/complaints/<int:complaint_id>', methods=['DELETE'])
def delete_complaint(complaint_id):
    """Delete complaint (admin/head only)"""
    try:
        user = require_admin_auth()
        if not user:
            return jsonify({'error': 'admin auth required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        emit_complaints_update()
        
        return jsonify({'message': 'deleted'}), 200
    
    except Exception as e:
        logger.error(f"Error deleting complaint: {e}")
        return jsonify({'error': str(e)}), 500


# ====== COMPLAINT MESSAGES ROUTES ======

@complaints_bp.route('/complaints/<int:complaint_id>/messages', methods=['GET'])
def get_complaint_messages(complaint_id):
    """Get messages for a specific complaint"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify access - user owns complaint, or is admin/head
        cursor.execute('SELECT user_id FROM complaints WHERE id = ?', (complaint_id,))
        complaint = cursor.fetchone()
        
        if not complaint:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404
        
        if user['role'] == 'user' and complaint['user_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get messages
        cursor.execute("""
            SELECT cm.id, cm.complaint_id, cm.sender_id, cm.message, cm.created_at,
                   u.name as sender_name, u.role as sender_role
            FROM complaint_messages cm
            LEFT JOIN users u ON cm.sender_id = u.id
            WHERE cm.complaint_id = ?
            ORDER BY cm.created_at ASC
        """, (complaint_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return jsonify({'messages': messages}), 200
        
    except Exception as e:
        logger.error(f"Error fetching complaint messages: {e}")
        return jsonify({'error': str(e)}), 500


@complaints_bp.route('/complaints/<int:complaint_id>/messages', methods=['POST'])
def send_complaint_message(complaint_id):
    """Send a message on a complaint"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify access
        cursor.execute('SELECT user_id FROM complaints WHERE id = ?', (complaint_id,))
        complaint = cursor.fetchone()
        
        if not complaint:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404
        
        if user['role'] == 'user' and complaint['user_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Insert message
        cursor.execute("""
            INSERT INTO complaint_messages (complaint_id, sender_id, message, created_at)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        """, (complaint_id, user['id'], message))
        
        message_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'id': message_id, 'message': 'Message sent'}), 201
        
    except Exception as e:
        logger.error(f"Error sending complaint message: {e}")
        return jsonify({'error': str(e)}), 500


# ====== COMPLAINT FEEDBACK ROUTES ======

@complaints_bp.route('/complaints/<int:complaint_id>/feedback', methods=['GET'])
def get_complaint_feedback(complaint_id):
    """Get feedback for a specific complaint"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get feedback for this complaint
        cursor.execute("""
            SELECT id, complaint_id, user_id, rating, message, created_at, updated_at
            FROM feedback
            WHERE complaint_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (complaint_id,))
        
        feedback = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if feedback:
            return jsonify({'feedback': dict(feedback)}), 200
        else:
            return jsonify({'feedback': None}), 200
        
    except Exception as e:
        logger.error(f"Error fetching complaint feedback: {e}")
        return jsonify({'error': str(e)}), 500


@complaints_bp.route('/complaints/<int:complaint_id>/feedback', methods=['POST'])
def create_complaint_feedback(complaint_id):
    """Submit feedback for a specific complaint"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        rating = data.get('rating')
        message = data.get('message', '').strip()
        
        if not rating:
            return jsonify({'error': 'Rating is required'}), 400
        
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        if not message:
            return jsonify({'error': 'Feedback message is required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify user owns the complaint
        cursor.execute('SELECT user_id FROM complaints WHERE id = ?', (complaint_id,))
        complaint = cursor.fetchone()
        
        if not complaint:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404
        
        if complaint['user_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'You can only add feedback to your own complaints'}), 403
        
        # Check if feedback already exists
        cursor.execute('SELECT id FROM feedback WHERE complaint_id = ? AND user_id = ?', (complaint_id, user['id']))
        existing = cursor.fetchone()
        
        if existing:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Feedback already exists. Use PUT to update.'}), 409
        
        # Insert feedback
        cursor.execute("""
            INSERT INTO feedback (complaint_id, user_id, user_name, user_email, rating, message, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now', 'localtime'))
        """, (complaint_id, user['id'], user.get('name', 'Unknown'), user.get('email', ''), rating, message))
        
        feedback_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User {user['id']} submitted feedback {feedback_id} for complaint {complaint_id}")
        return jsonify({'id': feedback_id, 'message': 'Feedback submitted successfully'}), 201
        
    except Exception as e:
        logger.error(f"Error creating complaint feedback: {e}")
        return jsonify({'error': str(e)}), 500


@complaints_bp.route('/complaints/<int:complaint_id>/feedback', methods=['PUT'])
def update_complaint_feedback(complaint_id):
    """Update feedback for a specific complaint"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        rating = data.get('rating')
        message = data.get('message', '').strip()
        
        if not rating:
            return jsonify({'error': 'Rating is required'}), 400
        
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        if not message:
            return jsonify({'error': 'Feedback message is required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Find existing feedback
        cursor.execute('SELECT id FROM feedback WHERE complaint_id = ? AND user_id = ?', (complaint_id, user['id']))
        existing = cursor.fetchone()
        
        if not existing:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No feedback found to update'}), 404
        
        # Update feedback
        cursor.execute("""
            UPDATE feedback 
            SET rating = ?, message = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (rating, message, existing['id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Feedback updated successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error updating complaint feedback: {e}")
        return jsonify({'error': str(e)}), 500


@complaints_bp.route('/complaints/<int:complaint_id>/feedback', methods=['DELETE'])
def delete_complaint_feedback(complaint_id):
    """Delete feedback for a specific complaint"""
    try:
        user = require_user_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Find existing feedback
        cursor.execute('SELECT id FROM feedback WHERE complaint_id = ? AND user_id = ?', (complaint_id, user['id']))
        existing = cursor.fetchone()
        
        if not existing:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No feedback found to delete'}), 404
        
        # Delete feedback
        cursor.execute('DELETE FROM feedback WHERE id = ?', (existing['id'],))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Feedback deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting complaint feedback: {e}")
        return jsonify({'error': str(e)}), 500


# Head admin routes
@complaints_bp.route('/head/complaints', methods=['GET'])
def head_list_complaints():
    """Head admin: List all complaints with filters"""
    user = require_head_auth()
    if not user:
        return jsonify({'error': 'head auth required'}), 401
    
    return list_complaints()


@complaints_bp.route('/head/complaints/<int:complaint_id>', methods=['PUT'])
def head_update_complaint(complaint_id):
    """Head admin: Update complaint status"""
    user = require_head_auth()
    if not user:
        return jsonify({'error': 'head auth required'}), 401
    
    return update_complaint(complaint_id)


@complaints_bp.route('/head/complaints/<int:complaint_id>', methods=['DELETE'])
def head_delete_complaint(complaint_id):
    """Head admin: Delete complaint"""
    user = require_head_auth()
    if not user:
        return jsonify({'error': 'head auth required'}), 401
    
    return delete_complaint(complaint_id)


# ====== MEDIA UPLOAD ENDPOINT ======

@complaints_bp.route('/upload-media', methods=['POST'])
def upload_media():
    """Upload media files for complaints"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400
    
    # Allowed extensions
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'avi', 'mov', 'mkv', 'pdf'}
    max_size = 1024 * 1024 * 1024  # 1GB per file
    
    uploaded_files = []
    errors = []
    
    uploads_dir = config.UPLOAD_FOLDER
    os.makedirs(uploads_dir, exist_ok=True)
    
    conn = get_db()
    cursor = conn.cursor()
    
    for file in files:
        if file.filename == '':
            continue
            
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            errors.append(f"{filename}: Invalid file type")
            continue
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Seek back to start
        
        if file_size > max_size:
            errors.append(f"{filename}: File too large (max 1GB)")
            continue
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(uploads_dir, unique_filename)
        
        try:
            file.save(file_path)
            
            # Get mime type
            mime_type = file.content_type or 'application/octet-stream'
            
            # Insert into database
            current_time = format_datetime_for_db()
            cursor.execute("""
                INSERT INTO media_files (user_id, file_name, file_path, mime_type, file_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user['id'], filename, unique_filename, mime_type, file_size, current_time))
            
            media_id = cursor.lastrowid
            
            uploaded_files.append({
                'id': media_id,
                'file_name': filename,
                'file_path': f"uploads/{unique_filename}",
                'mime_type': mime_type,
                'file_size': file_size
            })
            
        except Exception as e:
            logger.error(f"Error uploading file {filename}: {e}")
            errors.append(f"{filename}: Upload failed")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        'uploaded_files': uploaded_files,
        'errors': errors,
        'total_uploaded': len(uploaded_files)
    }), 200 if uploaded_files else 400


# Media file serving
@complaints_bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(config.UPLOAD_FOLDER, filename)


# ============================================
# PDF EXPORT ENDPOINTS
# ============================================

@complaints_bp.route('/my/complaints/export-pdf', methods=['GET'])
def export_user_complaints_pdf():
    """Export user's own complaints as PDF"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, u.name as username, u.email
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.user_id = ?
            ORDER BY c.created_at DESC
        ''', (user['id'],))
        
        complaints = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'my_complaints_{timestamp}.pdf'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, filename)
        
        generate_complaints_pdf(complaints, output_path)
        
        logger.info(f"User {user['id']} exported their complaints PDF")
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting user complaints PDF: {e}")
        return jsonify({'error': 'Failed to export PDF'}), 500


@complaints_bp.route('/complaints/<int:complaint_id>/export-pdf', methods=['GET'])
def export_complaint_detail_pdf(complaint_id):
    """Export a single complaint detail as PDF"""
    user = require_user_auth()
    if not user:
        return jsonify({'error': 'authentication required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check access - user can only export their own complaints
        cursor.execute('''
            SELECT c.*, u.name as username, u.email,
                   a.name as admin_name
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.id
            LEFT JOIN users a ON c.assigned_to = a.id
            WHERE c.id = ?
        ''', (complaint_id,))
        
        complaint = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not complaint:
            return jsonify({'error': 'Complaint not found'}), 404
        
        complaint_dict = dict(complaint)
        
        # Check if user owns this complaint or is admin/head
        if complaint_dict['user_id'] != user['id'] and user.get('role') not in ['admin', 'head']:
            return jsonify({'error': 'Access denied'}), 403
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'complaint_{complaint_id}_{timestamp}.pdf'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, filename)
        
        generate_complaint_detail_pdf(complaint_dict, output_path)
        
        logger.info(f"User {user['id']} exported complaint {complaint_id} PDF")
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting complaint detail PDF: {e}")
        return jsonify({'error': 'Failed to export PDF'}), 500
