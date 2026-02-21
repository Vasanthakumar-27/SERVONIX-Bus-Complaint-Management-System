"""Role-based notification service with database storage and real-time delivery"""
import logging
from datetime import datetime
from ..database.connection import get_db

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Centralized notification service that:
    1. Stores notifications in the database
    2. Delivers real-time notifications via SocketIO
    3. Supports role-based notification targeting
    4. Manages notification read status
    """
    
    # Notification types
    TYPES = {
        'COMPLAINT_CREATED': 'complaint_created',
        'COMPLAINT_ASSIGNED': 'complaint_assigned',
        'COMPLAINT_STATUS': 'complaint_status',
        'COMPLAINT_RESPONSE': 'complaint_response',
        'FEEDBACK_RECEIVED': 'feedback_received',
        'FEEDBACK_RESPONSE': 'feedback_response',
        'MESSAGE_RECEIVED': 'message_received',
        'SYSTEM_ALERT': 'system_alert',
        'ADMIN_ALERT': 'admin_alert',
    }
    
    def __init__(self, socketio_service=None):
        """
        Initialize notification service.
        
        Args:
            socketio_service: Optional SocketIOService instance for real-time delivery
        """
        self.socketio_service = socketio_service
        logger.info("NotificationService initialized")
    
    def set_socketio_service(self, socketio_service):
        """Set the SocketIO service (for delayed initialization)"""
        self.socketio_service = socketio_service
    
    def create_notification(self, user_id, notification_type, title, message, related_id=None):
        """
        Create a notification for a specific user.
        
        Args:
            user_id: Target user ID
            notification_type: Type from TYPES
            title: Notification title
            message: Notification message
            related_id: Optional related entity ID (complaint_id, feedback_id, etc.)
        
        Returns:
            int: Notification ID or None on failure
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO notifications (user_id, type, title, message, related_id, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (user_id, notification_type, title, message, related_id, 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            notification_id = cursor.lastrowid
            conn.commit()
            
            # Send real-time notification if SocketIO service is available
            if self.socketio_service:
                self.socketio_service.emit_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    message=message,
                    related_id=related_id
                )
            
            logger.info(f"Notification {notification_id} created for user {user_id}: {title}")
            return notification_id
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def notify_user(self, user_id, title, message, notification_type='system_alert', related_id=None):
        """Convenience method to notify a specific user"""
        return self.create_notification(user_id, notification_type, title, message, related_id)
    
    def notify_by_role(self, role, title, message, notification_type='system_alert', related_id=None, exclude_user_id=None):
        """
        Send notification to all users with a specific role.
        
        Args:
            role: User role ('admin', 'head', 'user')
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            related_id: Optional related entity ID
            exclude_user_id: Optional user ID to exclude
        
        Returns:
            int: Number of notifications sent
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            query = "SELECT id FROM users WHERE role = ? AND is_active = 1"
            params = [role]
            
            if exclude_user_id:
                query += " AND id != ?"
                params.append(exclude_user_id)
            
            cursor.execute(query, params)
            users = cursor.fetchall()
            
            count = 0
            for user in users:
                if self.create_notification(user['id'], notification_type, title, message, related_id):
                    count += 1
            
            logger.info(f"Sent {count} notifications to {role}s: {title}")
            return count
            
        except Exception as e:
            logger.error(f"Error notifying by role: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
    
    def notify_admins(self, title, message, notification_type='admin_alert', related_id=None, exclude_user_id=None):
        """Notify all admins"""
        return self.notify_by_role('admin', title, message, notification_type, related_id, exclude_user_id)
    
    def notify_heads(self, title, message, notification_type='admin_alert', related_id=None):
        """Notify all head users"""
        return self.notify_by_role('head', title, message, notification_type, related_id)
    
    def notify_district_admins(self, district_id, title, message, notification_type='admin_alert', related_id=None):
        """
        Notify all admins assigned to a specific district.
        
        Args:
            district_id: Target district ID
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            related_id: Optional related entity ID
        
        Returns:
            int: Number of notifications sent
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT ada.admin_id
                FROM admin_district_assignments ada
                JOIN users u ON ada.admin_id = u.id
                WHERE ada.district_id = ? AND u.is_active = 1
            """, (district_id,))
            
            admins = cursor.fetchall()
            
            count = 0
            for admin in admins:
                if self.create_notification(admin['admin_id'], notification_type, title, message, related_id):
                    count += 1
            
            logger.info(f"Sent {count} notifications to district {district_id} admins: {title}")
            return count
            
        except Exception as e:
            logger.error(f"Error notifying district admins: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
    
    # ============================================
    # COMPLAINT NOTIFICATION HELPERS
    # ============================================
    
    def notify_complaint_created(self, complaint_id, user_name, complaint_type, route_number=None):
        """Notify relevant parties when a new complaint is created"""
        message = f"New {complaint_type} complaint from {user_name}"
        if route_number:
            message += f" on route {route_number}"
        
        # Notify all admins about new complaint
        return self.notify_admins(
            title="New Complaint Received",
            message=message,
            notification_type=self.TYPES['COMPLAINT_CREATED'],
            related_id=complaint_id
        )
    
    def notify_complaint_assigned(self, complaint_id, admin_id, complaint_type):
        """Notify admin when a complaint is assigned to them"""
        return self.create_notification(
            user_id=admin_id,
            notification_type=self.TYPES['COMPLAINT_ASSIGNED'],
            title="Complaint Assigned to You",
            message=f"A {complaint_type} complaint has been assigned to you for review.",
            related_id=complaint_id
        )
    
    def notify_complaint_status_change(self, complaint_id, user_id, new_status, admin_name=None):
        """Notify user when their complaint status changes"""
        status_messages = {
            'in-progress': 'Your complaint is now being reviewed.',
            'resolved': 'Your complaint has been resolved.',
            'rejected': 'Your complaint has been reviewed and closed.'
        }
        message = status_messages.get(new_status, f'Your complaint status changed to {new_status}.')
        if admin_name:
            message += f" Handled by {admin_name}."
        
        return self.create_notification(
            user_id=user_id,
            notification_type=self.TYPES['COMPLAINT_STATUS'],
            title=f"Complaint Status: {new_status.title().replace('-', ' ')}",
            message=message,
            related_id=complaint_id
        )
    
    def notify_complaint_response(self, complaint_id, user_id, admin_name):
        """Notify user when admin responds to their complaint"""
        return self.create_notification(
            user_id=user_id,
            notification_type=self.TYPES['COMPLAINT_RESPONSE'],
            title="Response to Your Complaint",
            message=f"{admin_name} has responded to your complaint.",
            related_id=complaint_id
        )
    
    # ============================================
    # FEEDBACK NOTIFICATION HELPERS
    # ============================================
    
    def notify_feedback_received(self, feedback_id, user_name, feedback_type):
        """Notify admins when new feedback is received"""
        return self.notify_admins(
            title="New Feedback Received",
            message=f"New {feedback_type} feedback from {user_name}.",
            notification_type=self.TYPES['FEEDBACK_RECEIVED'],
            related_id=feedback_id
        )
    
    def notify_feedback_response(self, feedback_id, user_id, admin_name):
        """Notify user when their feedback gets a response"""
        return self.create_notification(
            user_id=user_id,
            notification_type=self.TYPES['FEEDBACK_RESPONSE'],
            title="Response to Your Feedback",
            message=f"{admin_name} has responded to your feedback.",
            related_id=feedback_id
        )
    
    # ============================================
    # NOTIFICATION RETRIEVAL & MANAGEMENT
    # ============================================
    
    def get_user_notifications(self, user_id, limit=50, include_read=True):
        """Get notifications for a user"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT id, type, title, message, related_id, is_read, created_at
                FROM notifications
                WHERE user_id = ?
            """
            params = [user_id]
            
            if not include_read:
                query += " AND is_read = 0"
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_unread_count(self, user_id):
        """Get count of unread notifications for a user"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) as count FROM notifications
                WHERE user_id = ? AND is_read = 0
            """, (user_id,))
            
            result = cursor.fetchone()
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
    
    def mark_as_read(self, notification_id, user_id):
        """Mark a notification as read"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE notifications 
                SET is_read = 1, read_at = ?
                WHERE id = ? AND user_id = ?
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), notification_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def mark_all_as_read(self, user_id):
        """Mark all notifications as read for a user"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE notifications 
                SET is_read = 1, read_at = ?
                WHERE user_id = ? AND is_read = 0
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
            
            conn.commit()
            return cursor.rowcount
            
        except Exception as e:
            logger.error(f"Error marking all as read: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
    
    def delete_notification(self, notification_id, user_id):
        """Delete a notification"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM notifications WHERE id = ? AND user_id = ?
            """, (notification_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def delete_old_notifications(self, days=30):
        """Delete notifications older than specified days"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM notifications 
                WHERE created_at < datetime('now', ?)
            """, (f'-{days} days',))
            
            deleted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Deleted {deleted} notifications older than {days} days")
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting old notifications: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()


# Singleton instance for import
_notification_service = None


def get_notification_service():
    """Get the notification service singleton"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def create_notification_service(socketio_service=None):
    """Factory function to create NotificationService instance"""
    global _notification_service
    _notification_service = NotificationService(socketio_service)
    return _notification_service
