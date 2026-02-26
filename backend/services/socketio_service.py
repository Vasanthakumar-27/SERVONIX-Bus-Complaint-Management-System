"""SocketIO event handlers for real-time updates"""
import logging
from flask_socketio import emit

logger = logging.getLogger(__name__)


class SocketIOService:
    """Handles Socket.IO events and real-time communications"""
    
    def __init__(self, socketio, get_db_func):
        self.socketio = socketio
        self.get_db = get_db_func
        self.connected_users = {}  # Store user_id -> session_id mapping
        
        # Register event handlers
        self._register_handlers()
        logger.info("SocketIOService initialized")
    
    def _register_handlers(self):
        """Register Socket.IO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            from flask import request
            client_ip = request.remote_addr
            logger.info(f"Client connected - IP: {client_ip}, Session ID: {request.sid}")
            try:
                emit('connection_response', {'status': 'connected', 'message': 'Successfully connected to SERVONIX'})
            except Exception as e:
                logger.error(f"Error sending connection response: {e}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            # Remove from connected users
            user_id_to_remove = None
            from flask import request
            session_id = request.sid
            
            for user_id, sid in list(self.connected_users.items()):
                if sid == session_id:
                    user_id_to_remove = user_id
                    break
            
            if user_id_to_remove:
                del self.connected_users[user_id_to_remove]
                logger.info(f"User {user_id_to_remove} disconnected - Session ID: {session_id}")
            else:
                logger.info(f"Client disconnected - Session ID: {session_id}")
        
        @self.socketio.on('register')
        def handle_register(data):
            """Register user session for targeted notifications"""
            user_id = data.get('user_id')
            
            from flask import request
            session_id = request.sid
            
            if user_id:
                # Register by user_id
                self.connected_users[user_id] = session_id
                logger.info(f"User {user_id} registered for real-time updates - Session ID: {session_id}")
                try:
                    emit('register_response', {'status': 'success', 'user_id': user_id})
                except Exception as e:
                    logger.error(f"Error sending register response: {e}")
            else:
                logger.warning(f"Register request received without user_id - Session ID: {session_id}")
                try:
                    emit('register_response', {'status': 'error', 'message': 'user_id required'})
                except Exception as e:
                    logger.error(f"Error sending register error response: {e}")
        
        @self.socketio.on('mark_notification_read')
        def handle_mark_notification_read(data):
            """Handle notification read status update"""
            notification_id = data.get('notification_id')
            user_id = data.get('user_id')
            
            if not notification_id or not user_id:
                emit('notification_update_response', {
                    'status': 'error',
                    'message': 'notification_id and user_id required'
                })
                return
            
            try:
                conn = self.get_db()
                cursor = conn.cursor()
                
                # Update notification
                cursor.execute("""
                    UPDATE notifications 
                    SET is_read = 1 
                    WHERE id = ? AND user_id = ?
                """, (notification_id, user_id))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                emit('notification_update_response', {
                    'status': 'success',
                    'notification_id': notification_id
                })
                
                logger.info(f"Notification {notification_id} marked as read by user {user_id}")
                
            except Exception as e:
                logger.error(f"Error marking notification as read: {e}")
                emit('notification_update_response', {
                    'status': 'error',
                    'message': str(e)
                })
        
        @self.socketio.on('get_notifications')
        def handle_get_notifications(data):
            """Fetch user notifications via Socket.IO"""
            user_id = data.get('user_id')
            include_read = data.get('include_read', True)
            
            if not user_id:
                emit('notifications_response', {
                    'status': 'error',
                    'message': 'user_id required'
                })
                return
            
            try:
                conn = self.get_db()
                cursor = conn.cursor()
                
                query = """
                    SELECT id, type, message, related_id, is_read, created_at
                    FROM notifications
                    WHERE user_id = ?
                """
                params = [user_id]
                
                if not include_read:
                    query += " AND is_read = 0"
                
                query += " ORDER BY created_at DESC LIMIT 50"
                
                cursor.execute(query, params)
                notifications = [dict(row) for row in cursor.fetchall()]
                
                cursor.close()
                conn.close()
                
                emit('notifications_response', {
                    'status': 'success',
                    'notifications': notifications
                })
                
            except Exception as e:
                logger.error(f"Error fetching notifications: {e}")
                emit('notifications_response', {
                    'status': 'error',
                    'message': str(e)
                })
    
    def emit_complaint_update(self, complaint_id, action, data=None):
        """
        Emit complaint update to all connected clients
        
        Args:
            complaint_id: ID of the complaint
            action: Type of action (created, updated, deleted, status_changed)
            data: Additional data to send
        """
        try:
            self.socketio.emit('complaint_update', {
                'complaint_id': complaint_id,
                'action': action,
                'data': data or {},
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"Emitted complaint update: {complaint_id} - {action}")
        except Exception as e:
            logger.error(f"Error emitting complaint update: {e}")
    
    def emit_complaint_update(self, action, complaint_id, data=None):
        """
        Emit complaint update to all connected clients
        
        Args:
            action: Type of action (created, updated, deleted, status_changed)
            complaint_id: ID of the complaint
            data: Additional data to send
        """
        try:
            self.socketio.emit('complaints_updated', {
                'complaint_id': complaint_id,
                'action': action,
                'data': data or {},
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"Emitted complaints_updated: {complaint_id} - {action}")
        except Exception as e:
            logger.error(f"Error emitting complaint update: {e}")
    
    def emit_complaint_assigned(self, complaint_id, admin_id):
        """
        Emit complaint assignment to specific admin
        
        Args:
            complaint_id: ID of the complaint
            admin_id: ID of the admin assigned
        """
        try:
            session_id = self.connected_users.get(admin_id)
            if session_id:
                self.socketio.emit('complaint_assigned', {
                    'complaint_id': complaint_id,
                    'timestamp': datetime.now().isoformat()
                }, room=session_id)
                logger.info(f"Emitted complaint_assigned to admin {admin_id}")
            
            # Also emit general complaints update
            self.emit_complaint_update('assigned', complaint_id, {'admin_id': admin_id})
        except Exception as e:
            logger.error(f"Error emitting complaint assignment: {e}")
    
    def emit_complaint_status_changed(self, complaint_id, old_status, new_status):
        """
        Emit complaint status change to all connected clients
        
        Args:
            complaint_id: ID of the complaint
            old_status: Previous status
            new_status: New status
        """
        try:
            self.socketio.emit('complaint_status_changed', {
                'complaint_id': complaint_id,
                'old_status': old_status,
                'new_status': new_status,
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"Emitted complaint status change: {complaint_id} {old_status} -> {new_status}")
        except Exception as e:
            logger.error(f"Error emitting complaint status change: {e}")
    
    def emit_notification(self, user_id, notification_type, message, related_id=None):
        """
        Send notification to specific user via Socket.IO
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            message: Notification message
            related_id: Related entity ID (e.g., complaint_id)
        """
        try:
            # Get user's session ID if connected
            session_id = self.connected_users.get(user_id)
            
            notification_data = {
                'type': notification_type,
                'message': message,
                'related_id': related_id,
                'timestamp': datetime.now().isoformat()
            }
            
            if session_id:
                # Send to specific user
                self.socketio.emit('new_notification', notification_data, room=session_id)
                logger.info(f"Sent notification to user {user_id}")
            else:
                # User not connected, notification will be in database
                logger.debug(f"User {user_id} not connected, notification saved to database")
                
        except Exception as e:
            logger.error(f"Error emitting notification: {e}")
    
    def emit_notification_to_role(self, role, notification_type, message, related_id=None, exclude_user_id=None):
        """
        Send notification to all connected users with a specific role
        
        Args:
            role: User role ('admin', 'head', 'user')
            notification_type: Type of notification
            message: Notification message
            related_id: Related entity ID
            exclude_user_id: User ID to exclude from notification
        """
        try:
            # Get all users with this role
            conn = self.get_db()
            cursor = conn.cursor()
            
            query = "SELECT id FROM users WHERE role = ? AND is_active = 1"
            params = [role]
            
            if exclude_user_id:
                query += " AND id != ?"
                params.append(exclude_user_id)
            
            cursor.execute(query, params)
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            
            notification_data = {
                'type': notification_type,
                'message': message,
                'related_id': related_id,
                'timestamp': datetime.now().isoformat()
            }
            
            sent_count = 0
            for user in users:
                user_id = user['id']
                session_id = self.connected_users.get(user_id)
                if session_id:
                    self.socketio.emit('new_notification', notification_data, room=session_id)
                    sent_count += 1
            
            logger.info(f"Sent notification to {sent_count} connected {role}s")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error emitting role-based notification: {e}")
            return 0
    
    def emit_to_admins(self, notification_type, message, related_id=None, exclude_user_id=None):
        """Send notification to all connected admins"""
        return self.emit_notification_to_role('admin', notification_type, message, related_id, exclude_user_id)
    
    def emit_to_heads(self, notification_type, message, related_id=None):
        """Send notification to all connected heads"""
        return self.emit_notification_to_role('head', notification_type, message, related_id)
    
    def emit_district_notification(self, district_id, notification_type, message, related_id=None):
        """
        Send notification to all admins assigned to a specific district
        
        Args:
            district_id: Target district ID
            notification_type: Type of notification
            message: Notification message
            related_id: Related entity ID
        """
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ada.admin_id
                FROM admin_district_assignments ada
                JOIN users u ON ada.admin_id = u.id
                WHERE ada.district_id = ? AND u.is_active = 1
            """, (district_id,))
            
            admins = cursor.fetchall()
            cursor.close()
            conn.close()
            
            notification_data = {
                'type': notification_type,
                'message': message,
                'related_id': related_id,
                'district_id': district_id,
                'timestamp': datetime.now().isoformat()
            }
            
            sent_count = 0
            for admin in admins:
                session_id = self.connected_users.get(admin['admin_id'])
                if session_id:
                    self.socketio.emit('new_notification', notification_data, room=session_id)
                    sent_count += 1
            
            logger.info(f"Sent notification to {sent_count} district {district_id} admins")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error emitting district notification: {e}")
            return 0
    
    def broadcast_system_message(self, message, level='info'):
        """
        Broadcast system-wide message to all connected clients
        
        Args:
            message: Message to broadcast
            level: Message level (info, warning, error)
        """
        try:
            self.socketio.emit('system_message', {
                'message': message,
                'level': level,
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"Broadcast system message: {message}")
        except Exception as e:
            logger.error(f"Error broadcasting system message: {e}")
    
    def get_connected_users_count(self):
        """Get number of currently connected users"""
        return len(self.connected_users)
    
    def get_connected_users(self):
        """Get list of connected user IDs"""
        return list(self.connected_users.keys())
    
    def get_connected_users_by_role(self, role):
        """Get list of connected user IDs for a specific role"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE role = ? AND is_active = 1", (role,))
            role_users = {row['id'] for row in cursor.fetchall()}
            
            cursor.close()
            conn.close()
            
            return [uid for uid in self.connected_users.keys() if uid in role_users]
            
        except Exception as e:
            logger.error(f"Error getting connected users by role: {e}")
            return []


# Import datetime at module level
from datetime import datetime


def create_socketio_service(socketio, get_db_func):
    """Factory function to create SocketIOService instance"""
    return SocketIOService(socketio, get_db_func)
