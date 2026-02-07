"""Backend services package - Business logic layer"""
from .email_service import EmailService, email_service
from .file_service import FileService, create_file_service
from .socketio_service import SocketIOService, create_socketio_service
from .auto_assignment import AutoAssignmentService, create_auto_assignment_service
from .notification_service import NotificationService, create_notification_service, get_notification_service

__all__ = [
    'EmailService',
    'email_service',
    'FileService',
    'create_file_service',
    'SocketIOService',
    'create_socketio_service',
    'AutoAssignmentService',
    'create_auto_assignment_service',
    'NotificationService',
    'create_notification_service',
    'get_notification_service'
]
