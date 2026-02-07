# Service Layer Documentation

## Overview

The service layer contains business logic modules that are used across multiple route blueprints. This separates concerns and makes the codebase more maintainable and testable.

## Services

### 1. EmailService (`services/email_service.py`)

**Purpose**: Handles all email sending functionality including OTPs, notifications, and messages.

**Features**:
- ✅ Development mode (logs emails to console when SMTP not configured)
- ✅ Production mode (sends via SMTP)
- ✅ Beautiful HTML email templates
- ✅ OTP email for password reset
- ✅ Notification emails
- ✅ Complaint status update emails
- ✅ Welcome emails for new users

**Usage**:
```python
from services import email_service

# Send OTP email
email_service.send_otp_email(
    email='user@example.com',
    otp='123456',
    user_name='John Doe'
)

# Send notification
email_service.send_notification_email(
    email='user@example.com',
    subject='Your Complaint Update',
    message='Your complaint has been resolved.',
    recipient_name='John Doe'
)

# Send complaint notification
email_service.send_complaint_notification(
    email='user@example.com',
    complaint_id=123,
    complaint_type='Bus delay',
    status='resolved',
    recipient_name='John Doe'
)
```

**Configuration** (Environment Variables):
```env
EMAIL_SENDER=noreply@servonix.com
EMAIL_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**Note**: If `EMAIL_PASSWORD` is not set, emails will be logged to console (development mode).

---

### 2. FileService (`services/file_service.py`)

**Purpose**: Handles file uploads, validation, and storage with comprehensive security checks.

**Features**:
- ✅ File extension validation by category
- ✅ File size validation (category-based limits)
- ✅ Automatic filename sanitization
- ✅ Duplicate filename handling
- ✅ File metadata extraction
- ✅ File deletion
- ✅ Support for images, videos, and documents

**Allowed File Types**:
- **Images**: jpg, jpeg, png, gif, bmp, webp (max 10MB)
- **Videos**: mp4, avi, mov, mkv, wmv, flv, webm (max 100MB)
- **Documents**: pdf, doc, docx, txt, rtf (max 20MB)

**Usage**:
```python
from flask import current_app
from services import create_file_service

# Get file service from app config
file_service = current_app.config['file_service']

# Or create new instance
file_service = create_file_service(upload_folder='/path/to/uploads')

# Upload a file
result = file_service.upload_file(
    file=request.files['media'],
    allowed_categories=['images', 'videos'],
    subfolder='complaints',
    max_size=50*1024*1024  # 50MB custom limit
)

if result['success']:
    file_path = result['file_path']
    file_info = result['file_info']
    print(f"File saved: {file_path}")
else:
    error = result['error']
    print(f"Upload failed: {error}")

# Delete a file
success, error = file_service.delete_file('complaints/image_123.jpg')

# Get file information
info = file_service.get_file_info('complaints/image_123.jpg')
print(f"File size: {info['size_mb']:.2f} MB")
```

**In Routes**:
```python
@app.route('/upload', methods=['POST'])
def upload():
    file_service = current_app.config['file_service']
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    result = file_service.upload_file(
        request.files['file'],
        allowed_categories=['images']
    )
    
    if result['success']:
        return jsonify({'path': result['file_path']}), 200
    else:
        return jsonify({'error': result['error']}), 400
```

---

### 3. SocketIOService (`services/socketio_service.py`)

**Purpose**: Manages Socket.IO real-time events and communications.

**Features**:
- ✅ Client connection/disconnection handling
- ✅ User registration for targeted notifications
- ✅ Real-time notification updates
- ✅ Complaint update broadcasting
- ✅ System-wide message broadcasting
- ✅ Connected users tracking

**Socket.IO Events**:

**Client → Server**:
- `connect` - Client connects
- `disconnect` - Client disconnects
- `register` - Register user ID for notifications
  ```javascript
  socket.emit('register', {user_id: 123});
  ```
- `mark_notification_read` - Mark notification as read
  ```javascript
  socket.emit('mark_notification_read', {
    notification_id: 456,
    user_id: 123
  });
  ```
- `get_notifications` - Fetch user notifications
  ```javascript
  socket.emit('get_notifications', {
    user_id: 123,
    include_read: false
  });
  ```

**Server → Client**:
- `connection_response` - Connection confirmation
- `register_response` - Registration confirmation
- `new_notification` - New notification for user
- `complaint_update` - Complaint update event
- `system_message` - System-wide broadcast
- `notification_update_response` - Response to mark read
- `notifications_response` - Notification list

**Usage in Routes**:
```python
from flask import current_app

@app.route('/api/complaints', methods=['POST'])
def create_complaint():
    # ... create complaint logic ...
    
    # Notify via Socket.IO
    socketio_service = current_app.config['socketio_service']
    socketio_service.emit_complaint_update(
        complaint_id=new_id,
        action='created',
        data={'user_id': user['id']}
    )
    
    # Send notification to specific user
    socketio_service.emit_notification(
        user_id=admin_id,
        notification_type='new_complaint',
        message=f'New complaint #{new_id} assigned to you',
        related_id=new_id
    )
```

**Broadcast System Message**:
```python
socketio_service = current_app.config['socketio_service']
socketio_service.broadcast_system_message(
    message='System maintenance in 10 minutes',
    level='warning'
)
```

**Check Connected Users**:
```python
count = socketio_service.get_connected_users_count()
user_ids = socketio_service.get_connected_users()
print(f"{count} users connected: {user_ids}")
```

---

## Service Integration in Flask App

Services are initialized in `app.py` during application factory:

```python
from services import create_file_service, create_socketio_service

def create_app(config_object=config):
    app = Flask(__name__)
    # ... other initialization ...
    
    # Initialize services
    file_service = create_file_service(config_object.UPLOAD_FOLDER)
    socketio_service = create_socketio_service(socketio, get_db)
    
    # Store in app config for route access
    app.config['file_service'] = file_service
    app.config['socketio_service'] = socketio_service
    
    return app, socketio
```

---

## Architecture Benefits

### Separation of Concerns
- **Routes**: Handle HTTP requests/responses
- **Services**: Handle business logic
- **Models**: Handle data access (future work)

### Reusability
Services can be used across multiple routes without code duplication:
```python
# Used in auth.py for password reset
email_service.send_otp_email(email, otp, name)

# Used in complaints.py for status updates
email_service.send_complaint_notification(email, complaint_id, ...)

# Used in user.py for welcome emails
email_service.send_welcome_email(email, name)
```

### Testability
Services can be tested independently:
```python
# Unit test for file service
def test_file_validation():
    service = FileService('/tmp/uploads')
    assert service.is_allowed_file('image.jpg', ['images']) == True
    assert service.is_allowed_file('malware.exe') == False
```

### Maintainability
- Change email templates in one place (email_service.py)
- Update file validation rules in one place (file_service.py)
- Modify Socket.IO events in one place (socketio_service.py)

---

## Future Enhancements

### Planned Services:
1. **PDFService** - Generate PDF reports for complaints
2. **SMSService** - Send SMS notifications (optional)
3. **CacheService** - Redis caching for performance
4. **LoggingService** - Centralized logging with rotation
5. **AnalyticsService** - Track user behavior and metrics

---

## Error Handling

All services use Python logging for error tracking:

```python
import logging
logger = logging.getLogger(__name__)

try:
    # Service operation
    pass
except Exception as e:
    logger.error(f"Service error: {e}")
    return False, str(e)
```

Monitor logs for service errors:
```bash
tail -f logs/app.log | grep ERROR
```

---

## Production Checklist

### EmailService:
- [ ] Set `EMAIL_PASSWORD` environment variable
- [ ] Configure SMTP server (Gmail, SendGrid, etc.)
- [ ] Test email delivery
- [ ] Set up email monitoring/logs

### FileService:
- [ ] Configure `UPLOAD_FOLDER` path
- [ ] Set proper file permissions on upload folder
- [ ] Configure max file sizes per environment
- [ ] Set up file backup strategy
- [ ] Configure CDN for serving files (optional)

### SocketIOService:
- [ ] Configure `SOCKETIO_CORS_ALLOWED_ORIGINS`
- [ ] Test real-time events in production
- [ ] Set up Redis for horizontal scaling (optional)
- [ ] Monitor connected user count
- [ ] Set up Socket.IO logging

---

## Conclusion

The service layer provides a clean, maintainable architecture for the SERVONIX application. Each service is:
- **Self-contained**: All related logic in one module
- **Configurable**: Uses environment variables
- **Testable**: Can be unit tested independently
- **Reusable**: Used across multiple route blueprints
- **Production-ready**: With proper error handling and logging
