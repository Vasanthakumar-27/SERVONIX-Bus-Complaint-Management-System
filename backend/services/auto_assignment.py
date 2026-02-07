"""
STRICT AUTO-ASSIGNMENT SERVICE FOR COMPLAINTS

This service implements DETERMINISTIC complaint routing with the following rules:
1. Each complaint is assigned to EXACTLY ONE admin (or stays UNASSIGNED)
2. Routing is based on ROUTE MATCH ONLY - admin's assigned routes must contain the complaint route
3. If ONE admin matches → assign to them
4. If MULTIPLE admins match → assign to the one with HIGHEST priority for that route
5. If NO admin matches → complaint stays UNASSIGNED (for head admin to manually assign)

NO BROADCASTS: Each complaint goes to ONE admin, not broadcast to multiple.
NO WORKLOAD BALANCING: Routing is deterministic based on route assignment, not load.
"""
import logging
from database.connection import get_db

logger = logging.getLogger(__name__)


class AutoAssignmentService:
    """
    STRICT deterministic complaint assignment service.
    Routes complaints to admins based on route matching ONLY.
    """
    
    @staticmethod
    def find_admin_for_complaint(route_number=None, bus_number=None):
        """
        Find the SINGLE admin to assign a complaint to based on STRICT route matching.
        
        Algorithm:
        1. Get complaint route name/code (from route_number or bus lookup)
        2. Query admin_assignments for admins who have this route assigned
        3. If ONE match → return that admin
        4. If MULTIPLE matches → return admin with HIGHEST priority for this route
        5. If NO match → return None (complaint stays unassigned)
        
        Args:
            route_number: The route name/code from the complaint
            bus_number: Optional bus number to lookup route if route_number not provided
        
        Returns:
            dict: {'admin_id': int, 'reason': str} or None if no matching admin
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            complaint_route = route_number
            
            # If no route but bus provided, try to get route from bus
            if not complaint_route and bus_number:
                cursor.execute("""
                    SELECT r.name as route_name, r.code as route_code
                    FROM buses b
                    JOIN routes r ON b.route_id = r.id
                    WHERE b.bus_number = ? AND b.is_active = 1 AND r.is_active = 1
                """, (bus_number,))
                bus_route = cursor.fetchone()
                if bus_route:
                    complaint_route = bus_route['route_name'] or bus_route['route_code']
                    logger.info(f"Resolved route '{complaint_route}' from bus '{bus_number}'")
            
            if not complaint_route:
                logger.warning("No route provided for complaint - will be unassigned")
                return None
            
            # ===== STRICT ROUTE MATCHING QUERY =====
            # Find admin(s) whose assigned routes match the complaint route
            # Uses route.name or route.code for matching
            cursor.execute("""
                SELECT aa.admin_id, aa.priority, u.name as admin_name, r.name as route_name, r.code as route_code, r.district_id
                FROM admin_assignments aa
                JOIN routes r ON aa.route_id = r.id
                JOIN users u ON aa.admin_id = u.id
                WHERE (r.name = ? OR r.code = ?)
                  AND u.is_active = 1 
                  AND u.role = 'admin'
                  AND r.is_active = 1
                ORDER BY aa.priority DESC
                LIMIT 1
            """, (complaint_route, complaint_route))
            
            result = cursor.fetchone()
            
            if result:
                admin_id = result['admin_id']
                admin_name = result['admin_name']
                route_name = result['route_name'] or result['route_code']
                priority = result['priority']
                # sqlite3.Row doesn't support .get(), use try/except or direct access
                try:
                    district_id = result['district_id']
                except (KeyError, IndexError):
                    district_id = None
                
                logger.info(f"STRICT ASSIGNMENT: Complaint on route '{complaint_route}' → Admin '{admin_name}' (ID: {admin_id}, Priority: {priority})")
                
                return {
                    'admin_id': admin_id,
                    'district_id': district_id,
                    'reason': f"Route '{complaint_route}' is assigned to admin '{admin_name}'"
                }
            
            # No matching admin found
            logger.warning(f"NO ADMIN MATCH: Route '{complaint_route}' has no assigned admin - complaint will be UNASSIGNED")
            return None
            
        except Exception as e:
            logger.error(f"Error in strict auto-assignment: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_admin_for_route(route_name):
        """
        Get the admin assigned to a specific route.
        
        Args:
            route_name: The route name or code
            
        Returns:
            dict: Admin info or None
        """
        if not route_name:
            return None
            
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT aa.admin_id, u.name as admin_name, u.email, aa.priority
                FROM admin_assignments aa
                JOIN routes r ON aa.route_id = r.id
                JOIN users u ON aa.admin_id = u.id
                WHERE (r.name = ? OR r.code = ? OR r.route_number = ?)
                  AND u.is_active = 1 
                  AND r.is_active = 1
                ORDER BY aa.priority DESC
                LIMIT 1
            """, (route_name, route_name, route_name))
            
            result = cursor.fetchone()
            if result:
                return {
                    'admin_id': result['admin_id'],
                    'name': result['admin_name'],
                    'email': result['email'],
                    'priority': result['priority']
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting admin for route: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_routes_for_admin(admin_id):
        """
        Get all routes assigned to a specific admin.
        
        Args:
            admin_id: The admin's user ID
            
        Returns:
            list: List of route dicts
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT r.id, r.name, r.code, r.route_number, aa.priority, d.name as district_name
                FROM admin_assignments aa
                JOIN routes r ON aa.route_id = r.id
                LEFT JOIN districts d ON r.district_id = d.id
                WHERE aa.admin_id = ? AND r.is_active = 1
                ORDER BY aa.priority DESC
            """, (admin_id,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting routes for admin: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_admin_workload():
        """Get workload statistics for all admins"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT u.id, u.name, u.email,
                       COALESCE(pending.count, 0) as pending_count,
                       COALESCE(inprogress.count, 0) as in_progress_count,
                       COALESCE(resolved.count, 0) as resolved_count,
                       (SELECT COUNT(*) FROM admin_assignments WHERE admin_id = u.id) as assigned_routes_count
                FROM users u
                LEFT JOIN (
                    SELECT assigned_to, COUNT(*) as count 
                    FROM complaints WHERE status = 'pending' GROUP BY assigned_to
                ) pending ON u.id = pending.assigned_to
                LEFT JOIN (
                    SELECT assigned_to, COUNT(*) as count 
                    FROM complaints WHERE status = 'in-progress' GROUP BY assigned_to
                ) inprogress ON u.id = inprogress.assigned_to
                LEFT JOIN (
                    SELECT assigned_to, COUNT(*) as count 
                    FROM complaints WHERE status = 'resolved' GROUP BY assigned_to
                ) resolved ON u.id = resolved.assigned_to
                WHERE u.role = 'admin' AND u.is_active = 1
                ORDER BY u.name
            """)
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting admin workload: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def reassign_complaint(complaint_id, new_admin_id, reassigned_by):
        """
        Manually reassign a complaint to a different admin.
        This overrides the automatic assignment.
        
        Args:
            complaint_id: The complaint to reassign
            new_admin_id: The admin to assign to (can be None for unassigned)
            reassigned_by: The user performing the reassignment
            
        Returns:
            bool: True if successful
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            from utils.helpers import format_datetime_for_db
            
            # Get current assignment for logging
            cursor.execute("SELECT assigned_to, route FROM complaints WHERE id = ?", (complaint_id,))
            current = cursor.fetchone()
            if not current:
                logger.warning(f"Complaint {complaint_id} not found for reassignment")
                return False
                
            old_admin_id = current['assigned_to']
            route = current['route']
            
            # Update assignment
            cursor.execute("""
                UPDATE complaints 
                SET assigned_to = ?, updated_at = ?
                WHERE id = ?
            """, (new_admin_id, format_datetime_for_db(), complaint_id))
            
            conn.commit()
            
            logger.info(f"MANUAL REASSIGNMENT: Complaint {complaint_id} (route: {route}) reassigned from admin {old_admin_id} to {new_admin_id} by {reassigned_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error reassigning complaint: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_unassigned_complaints():
        """
        Get all complaints that have no admin assigned.
        These are complaints where the route didn't match any admin's assigned routes.
        
        Returns:
            list: List of unassigned complaint dicts
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT c.id, c.description, c.route, c.bus_number, c.status, c.created_at,
                       u.name as user_name
                FROM complaints c
                JOIN users u ON c.user_id = u.id
                WHERE c.assigned_to IS NULL AND c.status = 'pending'
                ORDER BY c.created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting unassigned complaints: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


# Factory function for consistency with other services
def create_auto_assignment_service():
    """Factory function to create AutoAssignmentService instance"""
    return AutoAssignmentService()
