"""District, Route, and Bus management routes - HEAD only operations"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

from ..database.connection import get_db
from ..utils.decorators import require_head_auth, require_admin_auth
from ..utils.helpers import format_datetime_for_db

logger = logging.getLogger(__name__)

districts_bp = Blueprint('districts', __name__, url_prefix='/api')


# ============================================
# DISTRICT MANAGEMENT ENDPOINTS
# ============================================

@districts_bp.route('/districts', methods=['GET'])
def list_districts():
    """List all districts (accessible by all authenticated users)"""
    try:
        # Allow admins and heads to view districts
        from utils.decorators import get_current_user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        query = "SELECT * FROM districts"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY name ASC"
        
        cursor.execute(query)
        districts = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'districts': districts})
    
    except Exception as e:
        logger.error(f"Error listing districts: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/districts', methods=['POST'])
def create_district():
    """Create a new district (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        data = request.get_json() or {}
        
        if not data.get('name') or not data.get('code'):
            return jsonify({'error': 'Name and code are required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check for duplicate name or code
        cursor.execute(
            "SELECT id, name, code FROM districts WHERE name = ? OR code = ?", 
            (data['name'], data['code'].upper())
        )
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            existing_data = dict(existing)
            if existing_data['name'] == data['name'] and existing_data['code'] == data['code'].upper():
                return jsonify({'error': f'District "{data["name"]}" with code "{data["code"]}" already exists'}), 409
            elif existing_data['name'] == data['name']:
                return jsonify({'error': f'District "{data["name"]}" already exists'}), 409
            else:
                return jsonify({'error': f'District code "{data["code"]}" already exists. Please try again.'}), 409
        
        cursor.execute("""
            INSERT INTO districts (name, code, description, is_active, created_by, created_at)
            VALUES (?, ?, ?, 1, ?, ?)
        """, (data['name'], data['code'].upper(), data.get('description', ''),
              user['id'], format_datetime_for_db()))
        
        district_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"District {district_id} created by head {user['id']}")
        return jsonify({'id': district_id, 'message': 'District created successfully'}), 201
    
    except Exception as e:
        logger.error(f"Error creating district: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/districts/<int:district_id>', methods=['GET'])
def get_district(district_id):
    """Get district details with routes and assigned admins"""
    try:
        from utils.decorators import get_current_user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get district
        cursor.execute("SELECT * FROM districts WHERE id = ?", (district_id,))
        district = cursor.fetchone()
        
        if not district:
            cursor.close()
            conn.close()
            return jsonify({'error': 'District not found'}), 404
        
        district_data = dict(district)
        
        # Get routes in this district
        cursor.execute("""
            SELECT id, code, name, start_point, end_point, is_active
            FROM routes WHERE district_id = ? ORDER BY code
        """, (district_id,))
        district_data['routes'] = [dict(row) for row in cursor.fetchall()]
        
        # Get assigned admins
        cursor.execute("""
            SELECT u.id, u.name, u.email, ada.is_primary
            FROM admin_district_assignments ada
            JOIN users u ON ada.admin_id = u.id
            WHERE ada.district_id = ?
            ORDER BY ada.is_primary DESC, u.name
        """, (district_id,))
        district_data['assigned_admins'] = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'district': district_data})
    
    except Exception as e:
        logger.error(f"Error getting district: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/districts/<int:district_id>', methods=['PUT'])
def update_district(district_id):
    """Update a district (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        data = request.get_json() or {}
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check district exists
        cursor.execute("SELECT id FROM districts WHERE id = ?", (district_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'District not found'}), 404
        
        updates = []
        params = []
        
        if 'name' in data:
            updates.append('name = ?')
            params.append(data['name'])
        if 'code' in data:
            updates.append('code = ?')
            params.append(data['code'].upper())
        if 'description' in data:
            updates.append('description = ?')
            params.append(data['description'])
        if 'is_active' in data:
            updates.append('is_active = ?')
            params.append(1 if data['is_active'] else 0)
        
        if updates:
            updates.append('updated_at = ?')
            params.append(format_datetime_for_db())
            params.append(district_id)
            
            cursor.execute(f"UPDATE districts SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'District updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating district: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/districts/<int:district_id>', methods=['DELETE'])
def delete_district(district_id):
    """Delete a district (HEAD only) - Soft delete by setting is_active=0"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE districts SET is_active = 0, updated_at = ? WHERE id = ?",
                      (format_datetime_for_db(), district_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'District not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"District {district_id} soft-deleted by head {user['id']}")
        return jsonify({'message': 'District deactivated successfully'})
    
    except Exception as e:
        logger.error(f"Error deleting district: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ROUTE MANAGEMENT ENDPOINTS
# ============================================

@districts_bp.route('/routes', methods=['GET'])
def list_routes():
    """List all routes with optional district filter"""
    try:
        from utils.decorators import get_current_user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        district_id = request.args.get('district_id')
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        conn = get_db()
        cursor = conn.cursor()
        
        query = """
            SELECT r.*, d.name as district_name
            FROM routes r
            LEFT JOIN districts d ON r.district_id = d.id
            WHERE 1=1
        """
        params = []
        
        if district_id:
            query += " AND r.district_id = ?"
            params.append(district_id)
        
        if not include_inactive:
            query += " AND r.is_active = 1"
        
        query += " ORDER BY r.code"
        
        cursor.execute(query, params)
        routes = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'routes': routes})
    
    except Exception as e:
        logger.error(f"Error listing routes: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/routes', methods=['POST'])
def create_route():
    """Create a new route (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        data = request.get_json() or {}
        
        # Accept both 'code' and 'route_number' as input
        route_code = data.get('code') or data.get('route_number')
        if not route_code or not data.get('name'):
            return jsonify({'error': 'Route code and name are required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check for duplicate route code or name in the same district
        if data.get('district_id'):
            cursor.execute(
                "SELECT id, name, code FROM routes WHERE (code = ? OR name = ?) AND district_id = ?", 
                (route_code, data['name'], data['district_id'])
            )
        else:
            cursor.execute(
                "SELECT id, name, code FROM routes WHERE code = ? OR name = ?", 
                (route_code, data['name'])
            )
        
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            existing_data = dict(existing)
            if existing_data['code'] == route_code and existing_data['name'] == data['name']:
                return jsonify({'error': f'Route "{data["name"]}" already exists in this district'}), 409
            elif existing_data['code'] == route_code:
                return jsonify({'error': f'Route code "{route_code}" already exists. Please try again.'}), 409
            else:
                return jsonify({'error': f'Route "{data["name"]}" already exists in this district'}), 409
        
        cursor.execute("""
            INSERT INTO routes (code, name, district_id, start_point, end_point, 
                               description, is_active, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (route_code, data['name'], data.get('district_id'),
              data.get('start_point', ''), data.get('end_point', ''),
              data.get('description', ''), user['id'], format_datetime_for_db()))
        
        route_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Route {route_id} created by head {user['id']}")
        return jsonify({'id': route_id, 'message': 'Route created successfully'}), 201
    
    except Exception as e:
        logger.error(f"Error creating route: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/routes/<int:route_id>', methods=['GET'])
def get_route(route_id):
    """Get route details with buses"""
    try:
        from utils.decorators import get_current_user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT r.*, d.name as district_name
            FROM routes r
            LEFT JOIN districts d ON r.district_id = d.id
            WHERE r.id = ?
        """, (route_id,))
        route = cursor.fetchone()
        
        if not route:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Route not found'}), 404
        
        route_data = dict(route)
        
        # Get buses on this route
        cursor.execute("""
            SELECT id, bus_number, bus_type, capacity, is_active
            FROM buses WHERE route_id = ? ORDER BY bus_number
        """, (route_id,))
        route_data['buses'] = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'route': route_data})
    
    except Exception as e:
        logger.error(f"Error getting route: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/routes/<int:route_id>', methods=['PUT'])
def update_route(route_id):
    """Update a route (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        data = request.get_json() or {}
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM routes WHERE id = ?", (route_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Route not found'}), 404
        
        updates = []
        params = []
        
        for field in ['code', 'name', 'district_id', 'start_point', 'end_point', 'description']:
            # Accept route_number as alias for code
            value = data.get(field) or (data.get('route_number') if field == 'code' else None)
            if value is not None:
                updates.append(f'{field} = ?')
                params.append(value)
        
        if 'is_active' in data:
            updates.append('is_active = ?')
            params.append(1 if data['is_active'] else 0)
        
        if updates:
            updates.append('updated_at = ?')
            params.append(format_datetime_for_db())
            params.append(route_id)
            
            cursor.execute(f"UPDATE routes SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Route updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating route: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/routes/<int:route_id>', methods=['DELETE'])
def delete_route(route_id):
    """Delete a route (HEAD only) - Soft delete"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE routes SET is_active = 0, updated_at = ? WHERE id = ?",
                      (format_datetime_for_db(), route_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Route not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Route deactivated successfully'})
    
    except Exception as e:
        logger.error(f"Error deleting route: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# BUS MANAGEMENT ENDPOINTS
# ============================================

@districts_bp.route('/buses', methods=['GET'])
def list_buses():
    """List all buses with optional route/district filter"""
    try:
        from utils.decorators import get_current_user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        route_id = request.args.get('route_id')
        district_id = request.args.get('district_id')
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        conn = get_db()
        cursor = conn.cursor()
        
        query = """
            SELECT b.*, r.code as route_code, r.name as route_name, d.name as district_name
            FROM buses b
            LEFT JOIN routes r ON b.route_id = r.id
            LEFT JOIN districts d ON r.district_id = d.id
            WHERE 1=1
        """
        params = []
        
        if route_id:
            query += " AND b.route_id = ?"
            params.append(route_id)
        
        if district_id:
            query += " AND r.district_id = ?"
            params.append(district_id)
        
        if not include_inactive:
            query += " AND b.is_active = 1"
        
        query += " ORDER BY b.bus_number"
        
        cursor.execute(query, params)
        buses = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'buses': buses})
    
    except Exception as e:
        logger.error(f"Error listing buses: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/buses', methods=['POST'])
def create_bus():
    """Create a new bus (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        data = request.get_json() or {}
        
        if not data.get('bus_number'):
            return jsonify({'error': 'Bus number is required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check for duplicate
        cursor.execute("SELECT id FROM buses WHERE bus_number = ?", (data['bus_number'],))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Bus with this number already exists'}), 409
        
        cursor.execute("""
            INSERT INTO buses (bus_number, route_id, bus_type, capacity, is_active, created_by, created_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (data['bus_number'], data.get('route_id'), data.get('bus_type', 'regular'),
              data.get('capacity', 40), user['id'], format_datetime_for_db()))
        
        bus_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Bus {bus_id} created by head {user['id']}")
        return jsonify({'id': bus_id, 'message': 'Bus created successfully'}), 201
    
    except Exception as e:
        logger.error(f"Error creating bus: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/buses/<int:bus_id>', methods=['PUT'])
def update_bus(bus_id):
    """Update a bus (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        data = request.get_json() or {}
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM buses WHERE id = ?", (bus_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Bus not found'}), 404
        
        updates = []
        params = []
        
        for field in ['bus_number', 'route_id', 'bus_type', 'capacity']:
            if field in data:
                updates.append(f'{field} = ?')
                params.append(data[field])
        
        if 'is_active' in data:
            updates.append('is_active = ?')
            params.append(1 if data['is_active'] else 0)
        
        if updates:
            updates.append('updated_at = ?')
            params.append(format_datetime_for_db())
            params.append(bus_id)
            
            cursor.execute(f"UPDATE buses SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Bus updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating bus: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/buses/<int:bus_id>', methods=['DELETE'])
def delete_bus(bus_id):
    """Delete a bus (HEAD only) - Soft delete"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE buses SET is_active = 0, updated_at = ? WHERE id = ?",
                      (format_datetime_for_db(), bus_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Bus not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Bus deactivated successfully'})
    
    except Exception as e:
        logger.error(f"Error deleting bus: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ADMIN DISTRICT ASSIGNMENT ENDPOINTS
# ============================================

@districts_bp.route('/my-assignments', methods=['GET'])
def get_my_assignments():
    """Get the logged-in admin's district/route assignments"""
    try:
        user = require_admin_auth()
        if not user:
            return jsonify({'error': 'Admin authorization required'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ada.*, d.name as district_name, d.code as district_code
            FROM admin_district_assignments ada
            JOIN districts d ON ada.district_id = d.id
            WHERE ada.admin_id = ?
            ORDER BY d.name
        """, (user['id'],))
        
        assignments = [dict(row) for row in cursor.fetchall()]
        
        # Also get route assignments if any
        cursor.execute("""
            SELECT aa.*, r.name as route_name, r.code as route_code,
                   d.name as district_name
            FROM admin_assignments aa
            LEFT JOIN routes r ON aa.route_id = r.id
            LEFT JOIN districts d ON aa.district_id = d.id
            WHERE aa.admin_id = ?
            ORDER BY d.name, r.name
        """, (user['id'],))
        
        route_assignments = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        # Combine results
        all_assignments = assignments + route_assignments
        
        return jsonify(all_assignments)
    
    except Exception as e:
        logger.error(f"Error getting my assignments: {e}")
        return jsonify({'error': str(e)}), 500

@districts_bp.route('/admin-assignments', methods=['GET'])
def list_admin_assignments():
    """List all admin-district assignments (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ada.*, u.name as admin_name, u.email as admin_email,
                   d.name as district_name, d.code as district_code
            FROM admin_district_assignments ada
            JOIN users u ON ada.admin_id = u.id
            JOIN districts d ON ada.district_id = d.id
            ORDER BY d.name, u.name
        """)
        
        assignments = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'assignments': assignments})
    
    except Exception as e:
        logger.error(f"Error listing admin assignments: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/admin-assignments', methods=['POST'])
def assign_admin_to_district():
    """Assign an admin to a district (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        data = request.get_json() or {}
        
        if not data.get('admin_id') or not data.get('district_id'):
            return jsonify({'error': 'admin_id and district_id are required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify admin exists and is an admin
        cursor.execute("SELECT id, role FROM users WHERE id = ?", (data['admin_id'],))
        admin = cursor.fetchone()
        if not admin or admin['role'] != 'admin':
            cursor.close()
            conn.close()
            return jsonify({'error': 'Invalid admin user'}), 400
        
        # Verify district exists
        cursor.execute("SELECT id FROM districts WHERE id = ? AND is_active = 1", (data['district_id'],))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Invalid or inactive district'}), 400
        
        # Check if assignment already exists
        cursor.execute("""
            SELECT id FROM admin_district_assignments 
            WHERE admin_id = ? AND district_id = ?
        """, (data['admin_id'], data['district_id']))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Admin is already assigned to this district'}), 409
        
        # If setting as primary, unset other primaries for this admin
        if data.get('is_primary'):
            cursor.execute("""
                UPDATE admin_district_assignments SET is_primary = 0 WHERE admin_id = ?
            """, (data['admin_id'],))
        
        cursor.execute("""
            INSERT INTO admin_district_assignments (admin_id, district_id, is_primary, assigned_by, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (data['admin_id'], data['district_id'], 1 if data.get('is_primary') else 0,
              user['id'], format_datetime_for_db()))
        
        assignment_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Admin {data['admin_id']} assigned to district {data['district_id']} by head {user['id']}")
        return jsonify({'id': assignment_id, 'message': 'Admin assigned to district successfully'}), 201
    
    except Exception as e:
        logger.error(f"Error assigning admin to district: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/admin-assignments/<int:assignment_id>', methods=['DELETE'])
def remove_admin_assignment(assignment_id):
    """Remove an admin from a district (HEAD only)"""
    try:
        user = require_head_auth()
        if not user:
            return jsonify({'error': 'Head authorization required'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM admin_district_assignments WHERE id = ?", (assignment_id,))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Assignment not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Admin assignment removed successfully'})
    
    except Exception as e:
        logger.error(f"Error removing admin assignment: {e}")
        return jsonify({'error': str(e)}), 500


@districts_bp.route('/admins/<int:admin_id>/districts', methods=['GET'])
def get_admin_districts(admin_id):
    """Get all districts assigned to an admin"""
    try:
        from utils.decorators import get_current_user
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.*, ada.is_primary
            FROM admin_district_assignments ada
            JOIN districts d ON ada.district_id = d.id
            WHERE ada.admin_id = ? AND d.is_active = 1
            ORDER BY ada.is_primary DESC, d.name
        """, (admin_id,))
        
        districts = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'districts': districts})
    
    except Exception as e:
        logger.error(f"Error getting admin districts: {e}")
        return jsonify({'error': str(e)}), 500


# Export for dropdown/autocomplete in complaint forms
@districts_bp.route('/lookup/routes', methods=['GET'])
def lookup_routes():
    """Quick lookup for routes (for complaint form autocomplete)"""
    try:
        q = request.args.get('q', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, name FROM routes 
            WHERE is_active = 1 AND (code LIKE ? OR name LIKE ?)
            ORDER BY code LIMIT 20
        """, (f'%{q}%', f'%{q}%'))
        
        routes = [{'value': row['code'], 'label': f"{row['code']} - {row['name']}"} 
                  for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'routes': routes})
    
    except Exception as e:
        logger.error(f"Error in route lookup: {e}")
        return jsonify({'routes': []})


@districts_bp.route('/lookup/buses', methods=['GET'])
def lookup_buses():
    """Quick lookup for buses (for complaint form autocomplete)"""
    try:
        q = request.args.get('q', '')
        route_code = request.args.get('route_number', '') or request.args.get('route_code', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        query = """
            SELECT b.bus_number, b.bus_type, r.code as route_code
            FROM buses b
            LEFT JOIN routes r ON b.route_id = r.id
            WHERE b.is_active = 1 AND b.bus_number LIKE ?
        """
        params = [f'%{q}%']
        
        if route_code:
            query += " AND r.code = ?"
            params.append(route_code)
        
        query += " ORDER BY b.bus_number LIMIT 20"
        
        cursor.execute(query, params)
        
        buses = [{'value': row['bus_number'], 
                  'label': f"{row['bus_number']} ({row['bus_type']})",
                  'route': row['route_code']} 
                 for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({'buses': buses})
    
    except Exception as e:
        logger.error(f"Error in bus lookup: {e}")
        return jsonify({'buses': []})
