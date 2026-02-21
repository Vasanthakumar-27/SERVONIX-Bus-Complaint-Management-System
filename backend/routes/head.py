"""Head admin routes"""
from flask import Blueprint, request, jsonify, send_file
import logging
import sqlite3
from werkzeug.security import generate_password_hash
import os
import tempfile
from datetime import datetime

from ..database.connection import get_db
from ..utils.decorators import require_head_auth
from ..utils.helpers import clamp_limit
from ..pdf_generator import generate_complaints_pdf, generate_users_pdf, generate_admin_pdf

logger = logging.getLogger(__name__)

head_bp = Blueprint('head', __name__, url_prefix='/api/head')


@head_bp.route('/admins', methods=['GET'])
def get_all_admins():
    """Get all admins with their district and route assignments"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all admins
        cursor.execute("""
            SELECT id, name, email, phone, is_active, created_at, profile_pic
            FROM users
            WHERE role = 'admin'
        """)
        admins = [dict(row) for row in cursor.fetchall()]
        
        # Get assignments for each admin - improved query with explicit handling
        for admin in admins:
            # First check if admin has any assignments at all
            cursor.execute("""
                SELECT COUNT(*) as count FROM admin_assignments WHERE admin_id = ?
            """, (admin['id'],))
            assignment_count = cursor.fetchone()['count']
            
            if assignment_count > 0:
                # Get district and route names
                cursor.execute("""
                    SELECT DISTINCT d.name as district_name, r.name as route_name
                    FROM admin_assignments aa
                    LEFT JOIN districts d ON aa.district_id = d.id
                    LEFT JOIN routes r ON aa.route_id = r.id
                    WHERE aa.admin_id = ?
                """, (admin['id'],))
                assignments = cursor.fetchall()
                
                districts = list(set([a['district_name'] for a in assignments if a['district_name']]))
                routes = list(set([a['route_name'] for a in assignments if a['route_name']]))
                
                admin['district'] = ', '.join(sorted(districts)) if districts else 'Not assigned'
                admin['routes'] = ', '.join(sorted(routes)) if routes else 'Not assigned'
                
                # Debug logging
                logger.debug(f"Admin {admin['id']} ({admin['name']}): assignments={assignment_count}, districts={districts}, routes={routes}")
            else:
                admin['district'] = 'Not assigned'
                admin['routes'] = 'Not assigned'
                logger.debug(f"Admin {admin['id']} ({admin['name']}): No assignments found")
        
        cursor.close()
        conn.close()

        return jsonify({'admins': admins})
        
    except Exception as e:
        logger.error(f"Error fetching admins: {e}")
        return jsonify({'error': 'Failed to fetch admins'}), 500


@head_bp.route('/admin-assignments/<int:admin_id>', methods=['GET'])
def get_admin_assignments(admin_id):
    """Get assignments for a specific admin (districts and routes)"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get admin assignments with district and route info
        cursor.execute("""
            SELECT aa.id, aa.admin_id, aa.district_id, aa.route_id, aa.priority,
                   d.name as district_name, d.code as district_code,
                   r.code as route_code, r.name as route_name
            FROM admin_assignments aa
            LEFT JOIN districts d ON aa.district_id = d.id
            LEFT JOIN routes r ON aa.route_id = r.id
            WHERE aa.admin_id = ?
            ORDER BY d.name, r.name
        """, (admin_id,))
        
        assignments = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        return jsonify({'assignments': assignments})
        
    except Exception as e:
        logger.error(f"Error fetching admin assignments: {e}")
        return jsonify({'error': 'Failed to fetch admin assignments'}), 500


@head_bp.route('/create-admin', methods=['POST'])
def create_admin():
    """Create a new admin with STRICT route assignments.
    
    Each admin is assigned to specific routes. Complaints will be routed 
    ONLY to the admin whose assigned routes match the complaint route.
    
    Request Body:
        name: Admin name (required)
        email: Admin email (required)
        password: Admin password (required)
        phone: Admin phone (optional)
        district_ids: List of district IDs (optional)
        route_ids: List of route IDs (required for complaint routing)
    """
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    data = request.get_json()
    name = data.get('name', data.get('username', '')).strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()
    
    # Get route and district assignments
    route_ids = data.get('route_ids', [])
    district_ids = data.get('district_ids', [])

    if not name or not email or not password:
        return jsonify({'error': 'name, email and password are required'}), 400

    if not route_ids:
        return jsonify({'error': 'At least one route must be assigned to the admin'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if admin exists
        cursor.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'User with this email already exists'}), 409

        # Validate route_ids exist
        for route_id in route_ids:
            cursor.execute("SELECT id, name FROM routes WHERE id = ? AND is_active = 1", (route_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'error': f'Route with ID {route_id} not found or inactive'}), 400

        # Create admin
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, phone, role)
            VALUES (?, ?, ?, ?, 'admin')
        """, (name, email, generate_password_hash(password), phone))
        admin_id = cursor.lastrowid

        # ===== STRICT ROUTE ASSIGNMENTS =====
        # Insert each route assignment with priority (use string values: 'high', 'medium', 'low')
        priority_levels = ['high', 'medium', 'low']
        for i, route_id in enumerate(route_ids):
            # Get district_id for this route
            cursor.execute("SELECT district_id FROM routes WHERE id = ?", (route_id,))
            route_info = cursor.fetchone()
            route_district_id = route_info['district_id'] if route_info else None
            
            # Assign priority based on order (first routes get higher priority)
            priority = priority_levels[min(i, len(priority_levels) - 1)]
            
            cursor.execute("""
                INSERT INTO admin_assignments (admin_id, route_id, district_id, priority, assigned_by, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (admin_id, route_id, route_district_id, priority, head['id']))
        
        # Log action with route details
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'create_admin', ?)
        """, (head['id'], head['name'], f"Created admin: {name} with {len(route_ids)} route(s)"))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Head {head['id']} created admin: {name} with routes: {route_ids}")
        return jsonify({
            'message': 'Admin created successfully',
            'admin_id': admin_id,
            'assigned_routes': len(route_ids)
        }), 201

    except Exception as e:
        logger.error(f"Error creating admin: {e}")
        return jsonify({'error': 'Failed to create admin'}), 500


@head_bp.route('/admins/<int:admin_id>/toggle', methods=['PUT'])
def toggle_admin_status(admin_id):
    """Toggle admin active status"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT is_active FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
        admin = cursor.fetchone()
        if not admin:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Admin not found'}), 404

        new_status = 0 if admin['is_active'] else 1
        cursor.execute("""
            UPDATE users SET is_active = ? WHERE id = ?
        """, (new_status, admin_id))

        # Log action
        status_text = 'activated' if new_status else 'deactivated'
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'toggle_admin', ?)
        """, (head['id'], head['name'], f"Admin #{admin_id} {status_text}"))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': f'Admin {status_text} successfully'}), 200

    except Exception as e:
        logger.error(f"Error toggling admin status: {e}")
        return jsonify({'error': 'Failed to toggle admin status'}), 500


@head_bp.route('/admins/<int:admin_id>/routes', methods=['PUT'])
def update_admin_routes(admin_id):
    """Update an admin's route assignments.
    
    This allows the head to add or change route assignments for existing admins.
    All existing route assignments are replaced with the new ones.
    
    Request Body:
        route_ids: List of route IDs to assign (required)
    """
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    data = request.get_json()
    route_ids = data.get('route_ids', [])
    
    if not route_ids:
        return jsonify({'error': 'At least one route must be assigned'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Verify admin exists
        cursor.execute("SELECT id, name FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
        admin = cursor.fetchone()
        if not admin:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Admin not found'}), 404

        # Validate route_ids exist
        for route_id in route_ids:
            cursor.execute("SELECT id FROM routes WHERE id = ? AND is_active = 1", (route_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'error': f'Route with ID {route_id} not found or inactive'}), 400

        # Delete existing assignments
        cursor.execute("DELETE FROM admin_assignments WHERE admin_id = ?", (admin_id,))

        # Insert new route assignments with priority (use string values: 'high', 'medium', 'low')
        priority_levels = ['high', 'medium', 'low']
        for i, route_id in enumerate(route_ids):
            # Get district_id for this route
            cursor.execute("SELECT district_id FROM routes WHERE id = ?", (route_id,))
            route_info = cursor.fetchone()
            route_district_id = route_info['district_id'] if route_info else None
            
            # Assign priority based on order (first routes get higher priority)
            priority = priority_levels[min(i, len(priority_levels) - 1)]
            
            cursor.execute("""
                INSERT INTO admin_assignments (admin_id, route_id, district_id, priority, assigned_by, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (admin_id, route_id, route_district_id, priority, head['id']))

        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'update_admin_routes', ?)
        """, (head['id'], head['name'], f"Updated routes for admin: {admin['name']} - {len(route_ids)} route(s)"))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Head {head['id']} updated routes for admin {admin_id}: {route_ids}")
        return jsonify({
            'message': 'Admin routes updated successfully',
            'admin_id': admin_id,
            'assigned_routes': len(route_ids)
        }), 200

    except Exception as e:
        logger.error(f"Error updating admin routes: {e}")
        return jsonify({'error': 'Failed to update admin routes'}), 500


@head_bp.route('/admins/<int:admin_id>/details', methods=['PUT'])
def update_admin_details(admin_id):
    """Update admin name, email, phone (HEAD only)"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        if not name and not email and not phone:
            return jsonify({'error': 'At least one field (name, email, phone) is required'}), 400

        conn = get_db()
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT id, name, email, phone FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
        admin = cursor.fetchone()
        if not admin:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Admin not found'}), 404
        
        # Build update query dynamically
        updates = []
        params = []
        if name:
            updates.append("name = ?")
            params.append(name)
        if email:
            # Check if email is already in use by another user
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, admin_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'error': 'Email already in use by another user'}), 409
            updates.append("email = ?")
            params.append(email)
        if phone:
            updates.append("phone = ?")
            params.append(phone)
        
        params.append(admin_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        
        # Log action
        old_values = f"name={admin['name']}, email={admin['email']}, phone={admin['phone']}"
        new_values = f"name={name or admin['name']}, email={email or admin['email']}, phone={phone or admin['phone']}"
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'update_admin_details', ?)
        """, (head['id'], head['name'], f"Updated admin {admin['name']}: {old_values} -> {new_values}"))
        
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Head {head['id']} updated admin {admin_id} details")
        return jsonify({
            'message': 'Admin details updated successfully',
            'admin_id': admin_id
        }), 200

    except Exception as e:
        logger.error(f"Error updating admin details: {e}")
        return jsonify({'error': 'Failed to update admin details'}), 500


@head_bp.route('/admins/<int:admin_id>/assignments', methods=['DELETE'])
def delete_admin_assignments(admin_id):
    """Delete all assignments for an admin (district and routes)"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT name FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
        admin = cursor.fetchone()
        if not admin:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Admin not found'}), 404
        
        # Delete all assignments
        cursor.execute("DELETE FROM admin_assignments WHERE admin_id = ?", (admin_id,))
        deleted_count = cursor.rowcount
        
        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'delete_admin_assignments', ?)
        """, (head['id'], head['name'], f"Deleted {deleted_count} assignments for admin: {admin['name']}"))
        
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Head {head['id']} deleted all assignments for admin {admin_id}")
        return jsonify({
            'message': 'Admin assignments deleted successfully',
            'deleted_count': deleted_count
        }), 200

    except Exception as e:
        logger.error(f"Error deleting admin assignments: {e}")
        return jsonify({'error': 'Failed to delete admin assignments'}), 500


@head_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
def delete_admin(admin_id):
    """Delete an admin"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM users WHERE id = ? AND role = 'admin'", (admin_id,))
        admin = cursor.fetchone()
        if not admin:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Admin not found'}), 404

        # Delete admin (cascades to assignments)
        cursor.execute("DELETE FROM users WHERE id = ?", (admin_id,))

        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'delete_admin', ?)
        """, (head['id'], head['name'], f"Deleted admin: {admin['name']}"))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Head {head['id']} deleted admin #{admin_id}")
        return jsonify({'message': 'Admin deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting admin: {e}")
        return jsonify({'error': 'Failed to delete admin'}), 500


@head_bp.route('/complaints', methods=['GET'])
def get_head_complaints():
    """Get complaints for head - supports filtering by unassigned.
    
    Query params:
    - unassigned=true: Show only complaints without an admin assigned
    - status: Filter by status
    - limit: Number of results (default 100)
    """
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        status = request.args.get('status')
        show_unassigned = request.args.get('unassigned', 'false').lower() == 'true'
        limit = clamp_limit(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT c.*, u.name as username, u.email, u.phone,
                   a.name as admin_username
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.id
            LEFT JOIN users a ON c.assigned_to = a.id AND a.role = 'admin'
        """
        conditions = []
        params = []
        
        # Filter by unassigned complaints
        if show_unassigned:
            conditions.append('c.assigned_to IS NULL')
        
        if status:
            conditions.append('c.status = ?')
            params.append(status)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += " ORDER BY c.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        complaints = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        return jsonify({'complaints': complaints})

    except Exception as e:
        logger.error(f"Error fetching head complaints: {e}")
        return jsonify({'error': 'Failed to fetch complaints'}), 500


@head_bp.route('/complaints/<int:complaint_id>', methods=['DELETE'])
def delete_head_complaint(complaint_id):
    """Delete a complaint (head only) - Clean implementation"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if complaint exists
        cursor.execute(
            "SELECT id, category, status, user_id FROM complaints WHERE id = ?",
            (complaint_id,)
        )
        complaint = cursor.fetchone()
        
        if not complaint:
            return jsonify({
                'success': False,
                'error': 'Complaint not found'
            }), 404

        # Delete complaint (database cascades will handle related records)
        cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))

        # Log the deletion action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details, timestamp)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (
            head['id'],
            head['name'],
            'delete_complaint',
            f"Deleted complaint #{complaint_id} (Category: {complaint['category']}, Status: {complaint['status']})"
        ))

        conn.commit()
        logger.info(f"Head {head['name']} (ID: {head['id']}) deleted complaint #{complaint_id}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Complaint deleted successfully',
            'deleted_id': complaint_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting complaint #{complaint_id}: {str(e)}")
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@head_bp.route('/complaints/<int:complaint_id>/assign', methods=['POST'])
def assign_complaint_to_admin(complaint_id):
    """Manually assign a complaint to an admin (used for unassigned complaints).
    
    This allows head admin to manually route complaints that couldn't be auto-assigned
    because the complaint route didn't match any admin's assigned routes.
    """
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    data = request.get_json()
    admin_id = data.get('admin_id')

    if not admin_id:
        return jsonify({'error': 'admin_id is required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if complaint exists
        cursor.execute("SELECT id, route FROM complaints WHERE id = ?", (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404

        # Check if admin exists and is active
        cursor.execute("SELECT id, name FROM users WHERE id = ? AND role = 'admin' AND is_active = 1", (admin_id,))
        admin = cursor.fetchone()
        if not admin:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Admin not found or inactive'}), 404

        # Assign complaint (using correct column name: assigned_to)
        cursor.execute("""
            UPDATE complaints
            SET assigned_to = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (admin_id, complaint_id))

        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'manual_assign_complaint', ?)
        """, (head['id'], head['name'], f"Manually assigned complaint #{complaint_id} (route: {complaint['route']}) to admin {admin['name']} (#{admin_id})"))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Head {head['id']} manually assigned complaint #{complaint_id} to admin #{admin_id}")
        return jsonify({'message': 'Complaint assigned successfully', 'admin_name': admin['name']}), 200

    except Exception as e:
        logger.error(f"Error assigning complaint: {e}")
        return jsonify({'error': 'Failed to assign complaint'}), 500


@head_bp.route('/complaints/<int:complaint_id>/unassign', methods=['POST'])
def unassign_complaint(complaint_id):
    """Unassign a complaint from admin (set assigned_to to NULL)"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE complaints
            SET assigned_to = NULL, updated_at = datetime('now')
            WHERE id = ?
        """, (complaint_id,))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Complaint not found'}), 404

        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'unassign_complaint', ?)
        """, (head['id'], head['name'], f"Unassigned complaint #{complaint_id}"))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Complaint unassigned successfully'}), 200

    except Exception as e:
        logger.error(f"Error unassigning complaint: {e}")
        return jsonify({'error': 'Failed to unassign complaint'}), 500


@head_bp.route('/complaints/bulk-assign', methods=['POST'])
def bulk_assign_complaints():
    """Bulk assign complaints to admins"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    data = request.get_json()
    assignments = data.get('assignments', [])  # [{complaint_id, admin_id}, ...]

    if not assignments:
        return jsonify({'error': 'assignments array is required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        success_count = 0
        for assignment in assignments:
            complaint_id = assignment.get('complaint_id')
            admin_id = assignment.get('admin_id')

            if complaint_id and admin_id:
                cursor.execute("""
                    UPDATE complaints
                    SET assigned_to = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (admin_id, complaint_id))
                if cursor.rowcount > 0:
                    success_count += 1

        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'bulk_assign', ?)
        """, (head['id'], head['name'], f"Bulk assigned {success_count} complaints"))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'message': f'Successfully assigned {success_count} complaints'
        }), 200

    except Exception as e:
        logger.error(f"Error bulk assigning complaints: {e}")
        return jsonify({'error': 'Failed to bulk assign complaints'}), 500


@head_bp.route('/stats', methods=['GET'])
def get_head_stats():
    """Get comprehensive statistics for head dashboard"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        stats = {}

        # Total complaints
        cursor.execute("SELECT COUNT(*) as count FROM complaints")
        stats['total_complaints'] = cursor.fetchone()['count']

        # Complaints by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM complaints
            GROUP BY status
        """)
        stats['by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}

        # Forwarded complaints
        cursor.execute("""
            SELECT COUNT(*) as count FROM complaints WHERE forwarded_to_head = 1
        """)
        stats['forwarded_complaints'] = cursor.fetchone()['count']

        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        stats['total_users'] = cursor.fetchone()['count']

        # Total admins
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
        stats['total_admins'] = cursor.fetchone()['count']

        # Active admins
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND is_active = 1")
        stats['active_admins'] = cursor.fetchone()['count']

        cursor.close()
        conn.close()

        return jsonify({'stats': stats})

    except Exception as e:
        logger.error(f"Error fetching head stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500


@head_bp.route('/users', methods=['GET'])
def get_all_users():
    """Get all users"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        limit = clamp_limit(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, email, phone, created_at
            FROM users
            WHERE role = 'user'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        users = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        return jsonify({'users': users})

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500


@head_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user (head only)"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT name, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        # Prevent deleting admin or head users
        if user['role'] in ['admin', 'head']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Cannot delete admin or head users via this endpoint'}), 403

        # Delete user (complaints will be preserved due to ON DELETE CASCADE not being on user_id)
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

        # Log action
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, admin_name, action, details)
            VALUES (?, ?, 'delete_user', ?)
        """, (head['id'], head['name'], f"Deleted user: {user['name']} (ID: {user_id})"))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Head {head['id']} deleted user #{user_id}")
        return jsonify({'message': 'User deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'Failed to delete user'}), 500


# ==================== PDF EXPORT ENDPOINTS ====================

@head_bp.route('/export/complaints-pdf', methods=['GET'])
def export_complaints_pdf():
    """Export complaints as PDF report"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Fetch all complaints with user details
        cursor.execute("""
            SELECT 
                c.id,
                c.bus_number,
                c.complaint_type as category,
                c.description,
                c.status,
                c.created_at,
                u.name as user_name,
                u.email as user_email,
                c.route_number as route_name
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.id
            ORDER BY c.created_at DESC
        """)
        
        complaints = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'complaints_report_{timestamp}.pdf'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, filename)
        
        generate_complaints_pdf(complaints, output_path)
        
        logger.info(f"Head {head['id']} exported complaints PDF")
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting complaints PDF: {e}")
        return jsonify({'error': 'Failed to export PDF'}), 500


@head_bp.route('/export/users-pdf', methods=['GET'])
def export_users_pdf():
    """Export users as PDF report (all or selected by IDs)"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        # Get optional IDs filter from query parameter
        ids_param = request.args.get('ids', '')
        selected_ids = [int(id.strip()) for id in ids_param.split(',') if id.strip()] if ids_param else []
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Fetch users (all or filtered by IDs)
        if selected_ids:
            placeholders = ','.join('?' * len(selected_ids))
            cursor.execute(f"""
                SELECT 
                    id,
                    name,
                    email,
                    phone,
                    created_at,
                    district
                FROM users
                WHERE role = 'user' AND id IN ({placeholders})
                ORDER BY created_at DESC
            """, selected_ids)
        else:
            cursor.execute("""
                SELECT 
                    id,
                    name,
                    email,
                    phone,
                    created_at,
                    district
                FROM users
                WHERE role = 'user'
                ORDER BY created_at DESC
            """)
        
        users = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = 'selected_users' if selected_ids else 'users_report'
        filename = f'{prefix}_{timestamp}.pdf'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, filename)
        
        generate_users_pdf(users, output_path)
        
        logger.info(f"Head {head['id']} exported users PDF ({len(users)} users)")
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting users PDF: {e}")
        return jsonify({'error': 'Failed to export PDF'}), 500


@head_bp.route('/export/admins-pdf', methods=['GET'])
def export_admins_pdf():
    """Export admins as PDF report (all or selected by IDs)"""
    head = require_head_auth()
    if not head:
        return jsonify({'error': 'head auth required'}), 401

    try:
        # Get optional IDs filter from query parameter
        ids_param = request.args.get('ids', '')
        selected_ids = [int(id.strip()) for id in ids_param.split(',') if id.strip()] if ids_param else []
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Fetch admins (all or filtered by IDs)
        if selected_ids:
            placeholders = ','.join('?' * len(selected_ids))
            cursor.execute(f"""
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    u.phone,
                    u.created_at,
                    u.is_active
                FROM users u
                WHERE u.role = 'admin' AND u.id IN ({placeholders})
                ORDER BY u.created_at DESC
            """, selected_ids)
        else:
            cursor.execute("""
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    u.phone,
                    u.created_at,
                    u.is_active
                FROM users u
                WHERE u.role = 'admin'
                ORDER BY u.created_at DESC
            """)
        
        admins = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = 'selected_admins' if selected_ids else 'admins_report'
        filename = f'{prefix}_{timestamp}.pdf'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, filename)
        
        generate_admin_pdf(admins, output_path)
        
        logger.info(f"Head {head['id']} exported admins PDF ({len(admins)} admins)")
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting admins PDF: {e}")
        return jsonify({'error': 'Failed to export PDF'}), 500
