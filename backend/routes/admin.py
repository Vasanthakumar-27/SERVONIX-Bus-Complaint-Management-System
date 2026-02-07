"""Admin-specific routes - Simplified to match actual database schema"""
from flask import Blueprint, request, jsonify, send_file
import logging
import os
import tempfile
from datetime import datetime

from database.connection import get_db
from utils.decorators import require_admin_auth
from utils.helpers import clamp_limit
from pdf_generator import generate_complaints_pdf, generate_users_pdf

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/complaints', methods=['GET'])
def get_admin_complaints():
    """Get complaints assigned to admin or all complaints"""
    admin = require_admin_auth()
    if not admin:
        return jsonify({'error': 'admin auth required'}), 401
    
    status = request.args.get('status')
    limit = clamp_limit(request.args.get('limit', 50))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        query = '''
            SELECT c.*, u.name as user_name, u.email as user_email
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.id
        '''
        params = []
        conditions = []
        
        # Admin ONLY sees complaints assigned to them (not unassigned)
        conditions.append('c.assigned_to = ?')
        params.append(admin['id'])
        
        if status:
            conditions.append('c.status = ?')
            params.append(status)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        query += ' ORDER BY c.created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        complaints = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'complaints': complaints})
        
    except Exception as e:
        logger.error(f"Error fetching admin complaints: {e}")
        return jsonify({'error': 'Failed to fetch complaints'}), 500


@admin_bp.route('/complaints/<int:complaint_id>/assign', methods=['PUT'])
def assign_complaint(complaint_id):
    """Assign complaint to self"""
    admin = require_admin_auth()
    if not admin:
        return jsonify({'error': 'admin auth required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE complaints 
            SET assigned_to = ?, status = 'in-progress'
            WHERE id = ?
        """, (admin['id'], complaint_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404
        
        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'assign_complaint', ?)
        """, (admin['id'], admin['name'], f"Assigned complaint #{complaint_id} to self"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Admin {admin['id']} assigned complaint #{complaint_id}")
        return jsonify({'message': 'Complaint assigned successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error assigning complaint: {e}")
        return jsonify({'error': 'Failed to assign complaint'}), 500


@admin_bp.route('/complaints/<int:complaint_id>/respond', methods=['PUT'])
def respond_to_complaint(complaint_id):
    """Admin response to complaint"""
    admin = require_admin_auth()
    if not admin:
        return jsonify({'error': 'admin auth required'}), 401
    
    data = request.get_json() or {}
    response = data.get('response', '').strip()
    status = data.get('status')
    
    if not response:
        return jsonify({'error': 'Response is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        updates = ['admin_response = ?', 'updated_at = datetime("now", "localtime")']
        params = [response]
        
        if status and status in ['in-progress', 'resolved', 'rejected']:
            updates.append('status = ?')
            params.append(status)
            
            if status == 'resolved':
                updates.append('resolved_at = datetime("now", "localtime")')
        
        params.append(complaint_id)
        
        cursor.execute(f"""
            UPDATE complaints 
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404
        
        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'respond_complaint', ?)
        """, (admin['id'], admin['name'], f"Responded to complaint #{complaint_id}"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Admin {admin['id']} responded to complaint #{complaint_id}")
        return jsonify({'message': 'Response submitted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error responding to complaint: {e}")
        return jsonify({'error': 'Failed to submit response'}), 500


@admin_bp.route('/stats', methods=['GET'])
def get_admin_stats():
    """Get admin dashboard statistics"""
    admin = require_admin_auth()
    if not admin:
        return jsonify({'error': 'admin auth required'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Total assigned complaints
        cursor.execute('''
            SELECT COUNT(*) FROM complaints WHERE assigned_to = ?
        ''', (admin['id'],))
        total_assigned = cursor.fetchone()[0]
        
        # Pending complaints
        cursor.execute('''
            SELECT COUNT(*) FROM complaints 
            WHERE assigned_to = ? AND status = 'pending'
        ''', (admin['id'],))
        pending = cursor.fetchone()[0]
        
        # In progress
        cursor.execute('''
            SELECT COUNT(*) FROM complaints 
            WHERE assigned_to = ? AND status = 'in-progress'
        ''', (admin['id'],))
        in_progress = cursor.fetchone()[0]
        
        # Resolved this month
        cursor.execute('''
            SELECT COUNT(*) FROM complaints 
            WHERE assigned_to = ? AND status = 'resolved'
            AND resolved_at >= datetime('now', 'start of month')
        ''', (admin['id'],))
        resolved_this_month = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_assigned': total_assigned,
            'pending': pending,
            'in_progress': in_progress,
            'resolved_this_month': resolved_this_month
        })
        
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500


@admin_bp.route('/activity-log', methods=['GET'])
def get_activity_log():
    """Get admin's activity log"""
    admin = require_admin_auth()
    if not admin:
        return jsonify({'error': 'admin auth required'}), 401
    
    limit = clamp_limit(request.args.get('limit', 20))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, action, details, created_at
            FROM admin_logs
            WHERE admin_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (admin['id'], limit))
        
        logs = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'logs': logs})
        
    except Exception as e:
        logger.error(f"Error fetching activity log: {e}")
        return jsonify({'error': 'Failed to fetch activity log'}), 500


@admin_bp.route('/export/complaints-pdf', methods=['GET'])
def export_complaints_pdf():
    """Export admin's assigned complaints as PDF"""
    admin = require_admin_auth()
    if not admin:
        return jsonify({'error': 'admin auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get complaints assigned to this admin
        cursor.execute('''
            SELECT c.*, u.name as username, u.email
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.assigned_to = ?
            ORDER BY c.created_at DESC
        ''', (admin['id'],))
        
        complaints = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'admin_complaints_{timestamp}.pdf'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, filename)
        
        generate_complaints_pdf(complaints, output_path)
        
        logger.info(f"Admin {admin['id']} exported complaints PDF")
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting admin complaints PDF: {e}")
        return jsonify({'error': 'Failed to export PDF'}), 500


@admin_bp.route('/export/users-pdf', methods=['GET'])
def export_users_pdf():
    """Export users list as PDF for admin"""
    admin = require_admin_auth()
    if not admin:
        return jsonify({'error': 'admin auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all regular users
        cursor.execute('''
            SELECT id, name, email, phone, district, created_at
            FROM users
            WHERE role = 'user'
            ORDER BY created_at DESC
        ''')
        
        users = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'users_report_{timestamp}.pdf'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, filename)
        
        generate_users_pdf(users, output_path)
        
        logger.info(f"Admin {admin['id']} exported users PDF")
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting users PDF: {e}")
        return jsonify({'error': 'Failed to export PDF'}), 500
