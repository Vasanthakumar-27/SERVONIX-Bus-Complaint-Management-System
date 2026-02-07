# Admin-Head Communication System Documentation

## Overview

A secure, internal messaging system enabling bidirectional communication between Admin and Head users without external email or chat applications. Messages are stored in the database with full tracking of status, replies, and complaint escalations.

---

## Features

### ✅ **Admin Capabilities**
- **Send Messages**: Compose messages to Head with subject and content
- **Link Complaints**: Optionally attach a complaint for escalation context
- **View Sent Messages**: See all sent messages with status badges
- **Track Responses**: View Head's replies and resolution status
- **Character Limit**: 5000 characters per message, 200 for subject

### ✅ **Head Capabilities**
- **Receive Messages**: Real-time notification of new messages
- **Reply to Messages**: Send responses to admin messages
- **Mark Resolved**: Close conversations when issue is addressed
- **Filter Messages**: View by status (all/unread/read/resolved)
- **Notification Badge**: Unread count in notification bar
- **Complaint Context**: View linked complaint details

### ✅ **Security Features**
- JWT authentication required for all endpoints
- Role-based access control (admin/head only)
- SQL injection prevention with parameterized queries
- XSS protection with HTML escaping
- Message length validation

---

## Database Schema

### Table: `admin_head_messages`

```sql
CREATE TABLE admin_head_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,               -- Foreign key to users table
    head_id INTEGER NOT NULL,                -- Foreign key to users table
    subject TEXT NOT NULL,                   -- Message subject (max 200 chars)
    message_content TEXT NOT NULL,           -- Message body (max 5000 chars)
    complaint_id INTEGER,                    -- Optional complaint link
    status TEXT NOT NULL DEFAULT 'unread',   -- unread/read/resolved
    reply_content TEXT,                      -- Head's reply
    replied_at DATETIME,                     -- When Head replied
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME,                        -- When Head first opened
    resolved_at DATETIME,                    -- When marked resolved
    
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (head_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE SET NULL,
    
    CHECK (status IN ('unread', 'read', 'resolved'))
);

-- Indexes for performance
CREATE INDEX idx_messages_head_id ON admin_head_messages(head_id, status);
CREATE INDEX idx_messages_admin_id ON admin_head_messages(admin_id);
CREATE INDEX idx_messages_complaint_id ON admin_head_messages(complaint_id);
CREATE INDEX idx_messages_created_at ON admin_head_messages(created_at DESC);
```

---

## Backend API Endpoints

### Base URL: `/api/messages`

---

### **Admin Endpoints**

#### **1. Send Message**
```http
POST /api/messages/admin/send
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "subject": "Urgent: Route 45 Issue",
  "message": "Multiple complaints about delayed buses on Route 45. Need immediate attention.",
  "complaint_id": 123  // Optional
}
```

**Success Response (201):**
```json
{
  "success": true,
  "message_id": 456,
  "message": "Message sent successfully"
}
```

**Error Responses:**
- `400`: Missing required fields or invalid data
- `401`: Admin authentication required
- `404`: Head user not found
- `500`: Server error

---

#### **2. Get Sent Messages**
```http
GET /api/messages/admin/sent
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response (200):**
```json
{
  "success": true,
  "total": 10,
  "messages": [
    {
      "id": 456,
      "subject": "Urgent: Route 45 Issue",
      "message_content": "Multiple complaints...",
      "complaint_id": 123,
      "complaint_number": "CMP-2024-00123",
      "status": "read",
      "reply_content": "I've assigned additional buses to Route 45...",
      "replied_at": "2026-02-01T10:30:00",
      "created_at": "2026-02-01T09:00:00",
      "read_at": "2026-02-01T09:15:00",
      "resolved_at": null,
      "head_name": "John Doe"
    }
  ]
}
```

---

#### **3. Get Message Details**
```http
GET /api/messages/admin/<message_id>
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response (200):**
```json
{
  "success": true,
  "message": {
    "id": 456,
    "subject": "Urgent: Route 45 Issue",
    "message_content": "Multiple complaints...",
    "complaint_id": 123,
    "complaint_number": "CMP-2024-00123",
    "complaint_description": "Bus was 30 minutes late...",
    "status": "read",
    "reply_content": "I've assigned additional buses...",
    "replied_at": "2026-02-01T10:30:00",
    "created_at": "2026-02-01T09:00:00",
    "head_name": "John Doe"
  }
}
```

---

### **Head Endpoints**

#### **4. Get Inbox**
```http
GET /api/messages/head/inbox?status=<filter>
```

**Query Parameters:**
- `status`: `all`, `unread`, `read`, `resolved` (default: all)

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response (200):**
```json
{
  "success": true,
  "messages": [...],
  "counts": {
    "total": 25,
    "unread": 5,
    "read": 15,
    "resolved": 5
  }
}
```

---

#### **5. Get Message (Auto-marks as read)**
```http
GET /api/messages/head/<message_id>
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response (200):**
```json
{
  "success": true,
  "message": {
    "id": 456,
    "subject": "Urgent: Route 45 Issue",
    "message_content": "Multiple complaints...",
    "admin_name": "Jane Smith",
    "admin_email": "jane@example.com",
    "admin_phone": "+1234567890",
    "complaint_id": 123,
    "complaint_number": "CMP-2024-00123",
    "complaint_description": "Bus was 30 minutes late...",
    "complaint_status": "pending",
    "status": "read",  // Auto-updated
    "read_at": "2026-02-01T09:15:00",
    "created_at": "2026-02-01T09:00:00"
  }
}
```

---

#### **6. Reply to Message**
```http
PUT /api/messages/head/<message_id>/reply
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "reply": "I've assigned additional buses to Route 45. Will monitor closely."
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Reply sent successfully"
}
```

**Error Responses:**
- `400`: Reply content required or too long
- `401`: Head authentication required
- `404`: Message not found
- `500`: Server error

---

#### **7. Mark Message as Resolved**
```http
PUT /api/messages/head/<message_id>/resolve
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Message marked as resolved"
}
```

---

#### **8. Get Unread Count**
```http
GET /api/messages/head/unread-count
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response (200):**
```json
{
  "success": true,
  "unread_count": 5
}
```

---

## Frontend Integration

### Admin Dashboard

#### **1. Access Messages**
- Click **"Messages"** button in controls bar
- Badge shows reply count (future enhancement)

#### **2. Compose Message**
```javascript
// Open compose modal
openComposeModal();

// Sends via API
sendMessage(event); // Called on form submit
```

**UI Components:**
- Subject input (max 200 chars)
- Message textarea (max 5000 chars with counter)
- Complaint dropdown (optional, loads pending complaints)
- Send/Cancel buttons

#### **3. View Sent Messages**
```javascript
// Load messages
loadMessages();

// Display list with status badges
displayMessages(messages);

// View details
viewMessage(messageId);
```

**Status Badges:**
- 🟡 **Pending**: Awaiting Head response
- 🟢 **Replied**: Head has responded
- ⚪ **Resolved**: Conversation closed

---

### Head Dashboard

#### **1. Notification Bar Integration**
```javascript
// Mail dropdown loads unread messages
loadDropdownContent('mail');

// Badge shows unread count
updateBadge('mailBadge', unreadCount);
```

#### **2. Full Inbox View**
```javascript
// Open full inbox
openMessagesInbox();

// Filter by status
filterMessages('unread'); // all, unread, read, resolved
```

#### **3. Message Actions**
```javascript
// View message (auto-marks as read)
openHeadMessageModal(messageId);

// Send reply
sendHeadReply(messageId);

// Mark resolved
resolveMessage(messageId);
```

**UI Components:**
- Filter buttons (All/Unread/Read/Resolved)
- Message list with status indicators
- Detail modal with reply form
- Mark resolved button

---

## User Workflows

### **Admin Sending Message**

1. Admin clicks "Messages" button
2. Clicks "Compose Message"
3. Fills in subject and message
4. (Optional) Selects complaint from dropdown
5. Clicks "Send Message"
6. Receives success toast
7. Message appears in sent list with "Pending" status

### **Head Responding**

1. Head sees unread badge on mail icon
2. Clicks mail icon → sees preview in dropdown
3. Clicks "View All Messages"
4. Sees filtered inbox (default: all)
5. Clicks message to open detail
6. Message auto-marked as "read"
7. Types reply in textarea
8. Clicks "Send Reply"
9. (Optional) Clicks "Mark Resolved"

### **Admin Viewing Reply**

1. Admin opens Messages section
2. Sees message status changed to "Replied"
3. Clicks message to view details
4. Sees Head's reply with timestamp
5. Status shows "Replied" or "Resolved"

---

## Message Status Lifecycle

```
unread → read → resolved
   ↓       ↓
   ↓    (reply sent)
   ↓       ↓
   └───────┘
```

**Status Transitions:**
1. **unread**: Initial state when admin sends message
2. **read**: Auto-set when Head opens message
3. **resolved**: Manually set by Head when issue is addressed

**Note**: Messages can be replied to in any status (unread/read), but resolved messages cannot be changed.

---

## Security Considerations

### Authentication
- All endpoints require JWT Bearer token
- Token validated on every request
- Expired tokens return 401 Unauthorized

### Authorization
- Admins can only send and view their own messages
- Heads can view all messages sent to them
- Cross-role access blocked

### Data Validation
- Subject: Required, max 200 characters
- Message: Required, max 5000 characters
- Reply: Required when replying, max 5000 characters
- complaint_id: Must exist in complaints table if provided

### SQL Injection Prevention
- All queries use parameterized statements
- No string concatenation in SQL

### XSS Protection
- Frontend escapes all user-generated content
- `escapeHtml()` function prevents script injection

---

## Performance Optimizations

### Database Indexes
```sql
-- Fast Head inbox queries
CREATE INDEX idx_messages_head_id ON admin_head_messages(head_id, status);

-- Fast Admin sent messages
CREATE INDEX idx_messages_admin_id ON admin_head_messages(admin_id);

-- Fast complaint linking
CREATE INDEX idx_messages_complaint_id ON admin_head_messages(complaint_id);

-- Chronological sorting
CREATE INDEX idx_messages_created_at ON admin_head_messages(created_at DESC);
```

### Frontend Caching
- Complaint dropdown cached during compose
- Sent messages cached with cache invalidation on send
- Notification badge updated every 3 seconds

---

## Error Handling

### Backend Errors
```python
try:
    # Database operations
except Exception as e:
    logger.error(f"Error: {str(e)}")
    return jsonify({'error': 'Failed to...'}), 500
```

### Frontend Errors
```javascript
try {
    const response = await fetch(url, options);
    if (!response.ok) {
        showToast(data.error || 'Operation failed', 'error');
    }
} catch (error) {
    console.error('Error:', error);
    showToast('Network error. Please try again.', 'error');
}
```

---

## Testing Checklist

### ✅ **Admin Tests**
- [ ] Compose message with all fields
- [ ] Compose message with complaint link
- [ ] Send message without complaint
- [ ] View sent messages list
- [ ] View message details with reply
- [ ] Check status badges update
- [ ] Verify character counter
- [ ] Test form validation

### ✅ **Head Tests**
- [ ] View unread badge count
- [ ] Open mail dropdown
- [ ] Click message in dropdown
- [ ] Open full inbox
- [ ] Filter by status (all/unread/read/resolved)
- [ ] View message details
- [ ] Send reply
- [ ] Mark message resolved
- [ ] Verify auto-read marking

### ✅ **Integration Tests**
- [ ] Admin sends → Head receives
- [ ] Head replies → Admin sees reply
- [ ] Head resolves → Status updates
- [ ] Complaint linking works
- [ ] Multiple messages ordering
- [ ] Concurrent access handling

---

## Future Enhancements

### Potential Features
1. **Attachments**: Upload files with messages
2. **Email Notifications**: Optional email alerts for new messages
3. **Message Templates**: Pre-written message templates
4. **Search**: Full-text search across messages
5. **Bulk Actions**: Mark multiple as read/resolved
6. **Message Priority**: Urgent/Normal/Low flags
7. **Read Receipts**: Track when admin reads Head's reply
8. **Message Threading**: Group related conversations
9. **Auto-Archive**: Auto-resolve old messages
10. **Export**: Download message history as PDF/CSV

---

## Troubleshooting

### Issue: Messages not appearing in inbox
**Solution:**
- Verify JWT token is valid
- Check user role is 'admin' or 'head'
- Confirm database has messages table
- Check browser console for errors

### Issue: Badge count not updating
**Solution:**
- Verify `/api/messages/head/unread-count` endpoint works
- Check browser console for fetch errors
- Ensure updateCounts() is called in interval

### Issue: Reply not sending
**Solution:**
- Check reply textarea has content
- Verify message exists and belongs to Head
- Check backend logs for errors
- Ensure HEAD authentication token is valid

---

## Maintenance

### Database Maintenance
```sql
-- Clean up resolved messages older than 90 days
DELETE FROM admin_head_messages 
WHERE status = 'resolved' 
  AND resolved_at < datetime('now', '-90 days');

-- Vacuum database
VACUUM;
```

### Monitoring
```python
# Log message statistics
SELECT 
    status, 
    COUNT(*) as count,
    AVG(julianday(replied_at) - julianday(created_at)) as avg_response_days
FROM admin_head_messages
WHERE replied_at IS NOT NULL
GROUP BY status;
```

---

## Support

For technical issues or questions:
- Check logs: `backend/logs/`
- Review error messages in browser console
- Verify database schema is correct
- Test API endpoints with Postman/curl

---

**System Version:** 1.0.0  
**Last Updated:** February 1, 2026  
**Author:** SERVONIX Development Team
