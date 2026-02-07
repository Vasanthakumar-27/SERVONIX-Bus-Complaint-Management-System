"""Dashboard statistics and analytics routes"""
from flask import Blueprint, request, jsonify
import logging

from database.connection import get_db
from utils.decorators import require_head_auth
from utils.helpers import clamp_limit

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """Get real-time dashboard statistics"""
    user = require_head_auth()
    if not user:
        return jsonify({'ok': False, 'error': 'head auth required'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Update current user's last_active
        cursor.execute("UPDATE users SET last_active = datetime('now', 'localtime') WHERE id = ?", (user['id'],))
        conn.commit()
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user' AND is_active = 1")
        total_users = cursor.fetchone()[0]
        
        # Active admins (logged in within last 15 minutes)
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE role IN ('admin', 'head') 
            AND is_active = 1 
            AND last_active >= datetime('now', '-15 minutes')
        """)
        active_admins = cursor.fetchone()[0]
        
        # Total complaints
        cursor.execute("SELECT COUNT(*) FROM complaints")
        total_complaints = cursor.fetchone()[0]
        
        # Pending complaints
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'pending'")
        pending_complaints = cursor.fetchone()[0]
        
        # In-progress complaints
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'in-progress'")
        inprogress_complaints = cursor.fetchone()[0]
        
        # Resolved complaints
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'resolved'")
        resolved_complaints = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'ok': True,
            'stats': {
                'total_users': total_users,
                'active_admins': active_admins,
                'total_complaints': total_complaints,
                'pending_complaints': pending_complaints,
                'inprogress_complaints': inprogress_complaints,
                'resolved_complaints': resolved_complaints
            }
        })
    except Exception as e:
        cursor.close()
        conn.close()
        logger.error(f"Error fetching dashboard stats: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@dashboard_bp.route('/online_users', methods=['GET'])
def get_online_users():
    """Get list of users active in last 15 minutes"""
    user = require_head_auth()
    if not user:
        return jsonify({'ok': False, 'error': 'head auth required'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Update current user's last_active
        cursor.execute("UPDATE users SET last_active = datetime('now', 'localtime') WHERE id = ?", (user['id'],))
        conn.commit()
        
        cursor.execute("""
            SELECT id, name, email, role, last_active 
            FROM users 
            WHERE is_active = 1 
            AND last_active >= datetime('now', '-15 minutes')
            ORDER BY last_active DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'role': row[3],
                'last_active': row[4]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({'ok': True, 'users': users})
    except Exception as e:
        cursor.close()
        conn.close()
        logger.error(f"Error fetching online users: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@dashboard_bp.route('/admin_logs', methods=['GET'])
def get_admin_logs():
    """Get recent admin activity logs"""
    user = require_head_auth()
    if not user:
        return jsonify({'ok': False, 'error': 'head auth required'}), 401
    
    limit = clamp_limit(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Update current user's last_active
        cursor.execute("UPDATE users SET last_active = datetime('now', 'localtime') WHERE id = ?", (user['id'],))
        conn.commit()
        
        # Query admin_logs - handle both old schema (admin_name, description) and new schema (details)
        cursor.execute("""
            SELECT al.id, al.admin_id, 
                   COALESCE(al.admin_name, u.name) as admin_name, 
                   al.action, 
                   COALESCE(al.description, al.details) as description, 
                   al.ip_address, 
                   al.created_at
            FROM admin_logs al
            LEFT JOIN users u ON al.admin_id = u.id
            ORDER BY al.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'id': row[0],
                'admin_id': row[1],
                'admin_name': row[2] or 'Unknown',
                'action': row[3],
                'description': row[4] or '',
                'ip_address': row[5] or '',
                'created_at': row[6]
            })
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM admin_logs")
        total = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({'ok': True, 'logs': logs, 'total': total})
    except Exception as e:
        cursor.close()
        conn.close()
        logger.error(f"Error fetching admin logs: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@dashboard_bp.route('/complaints_stats', methods=['GET'])
def get_complaints_stats():
    """Get detailed complaint statistics"""
    user = require_head_auth()
    if not user:
        return jsonify({'ok': False, 'error': 'head auth required'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Update current user's last_active
        cursor.execute("UPDATE users SET last_active = datetime('now', 'localtime') WHERE id = ?", (user['id'],))
        conn.commit()
        
        # Complaints by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM complaints
            GROUP BY status
        """)
        by_status = {}
        for row in cursor.fetchall():
            by_status[row[0]] = row[1]
        
        # Recent complaints (last 7 days)
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM complaints
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        recent_trends = []
        for row in cursor.fetchall():
            recent_trends.append({'date': row[0], 'count': row[1]})
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'ok': True,
            'stats': {
                'by_status': by_status,
                'recent_trends': recent_trends
            }
        })
    except Exception as e:
        cursor.close()
        conn.close()
        logger.error(f"Error fetching complaints stats: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500
