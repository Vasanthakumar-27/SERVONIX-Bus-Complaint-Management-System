-- ==================== NOTIFICATION SYSTEM SQL QUERIES ====================
-- Complete SQL reference for the real-time notification system

-- ==================== TABLE SCHEMAS ====================

-- User Notifications Table
CREATE TABLE IF NOT EXISTS user_notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('reply', 'status_resolved', 'feedback', 'message')),
  message TEXT NOT NULL,
  related_id INTEGER DEFAULT NULL,
  is_read INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Admin Notifications Table (from Head)
CREATE TABLE IF NOT EXISTS admin_notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_id INTEGER NOT NULL,
  sender_id INTEGER NOT NULL,
  message TEXT NOT NULL,
  is_read INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Head Notifications Table
CREATE TABLE IF NOT EXISTS head_notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL CHECK (type IN ('reply', 'status_update', 'feedback', 'new_complaint', 'admin_activity')),
  message TEXT NOT NULL,
  related_id INTEGER DEFAULT NULL,
  is_read INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== CREATE NOTIFICATIONS ====================

-- Create User Notification
INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
VALUES (?, ?, ?, ?, 0);

-- Example: Admin replied to complaint
INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
VALUES (123, 'reply', 'Admin replied to your complaint #456', 456, 0);

-- Example: Status resolved
INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
VALUES (123, 'status_resolved', 'Your complaint #456 has been resolved', 456, 0);

-- Create Admin Notification
INSERT INTO admin_notifications (admin_id, sender_id, message, is_read)
VALUES (?, ?, ?, 0);

-- Example: Head sends message to admin
INSERT INTO admin_notifications (admin_id, sender_id, message, is_read)
VALUES (45, 1, 'Please review the pending complaints in your assigned routes', 0);

-- Create Head Notification
INSERT INTO head_notifications (type, message, related_id, is_read)
VALUES (?, ?, ?, 0);

-- Example: New complaint
INSERT INTO head_notifications (type, message, related_id, is_read)
VALUES ('new_complaint', 'New complaint #789 submitted by John Doe', 789, 0);

-- Example: Admin activity
INSERT INTO head_notifications (type, message, related_id, is_read)
VALUES ('admin_activity', 'Admin Jane resolved complaint #789', 789, 0);

-- ==================== RETRIEVE NOTIFICATIONS ====================

-- Get User Notifications (all)
SELECT id, type, message, related_id, is_read, created_at
FROM user_notifications
WHERE user_id = ?
ORDER BY created_at DESC
LIMIT ?;

-- Get User Notifications (unread only)
SELECT id, type, message, related_id, is_read, created_at
FROM user_notifications
WHERE user_id = ? AND is_read = 0
ORDER BY created_at DESC
LIMIT ?;

-- Get Admin Notifications with Sender Name
SELECT n.id, n.message, n.is_read, n.created_at,
       u.name as sender_name
FROM admin_notifications n
LEFT JOIN users u ON n.sender_id = u.id
WHERE n.admin_id = ?
ORDER BY n.created_at DESC
LIMIT ?;

-- Get Admin Notifications (unread only)
SELECT n.id, n.message, n.is_read, n.created_at,
       u.name as sender_name
FROM admin_notifications n
LEFT JOIN users u ON n.sender_id = u.id
WHERE n.admin_id = ? AND n.is_read = 0
ORDER BY n.created_at DESC
LIMIT ?;

-- Get Head Notifications (all)
SELECT id, type, message, related_id, is_read, created_at
FROM head_notifications
ORDER BY created_at DESC
LIMIT ?;

-- Get Head Notifications (unread only)
SELECT id, type, message, related_id, is_read, created_at
FROM head_notifications
WHERE is_read = 0
ORDER BY created_at DESC
LIMIT ?;

-- ==================== MARK AS READ ====================

-- Mark User Notification as Read
UPDATE user_notifications
SET is_read = 1
WHERE id = ? AND user_id = ?;

-- Mark Admin Notification as Read
UPDATE admin_notifications
SET is_read = 1
WHERE id = ? AND admin_id = ?;

-- Mark Head Notification as Read
UPDATE head_notifications
SET is_read = 1
WHERE id = ?;

-- Mark All User Notifications as Read
UPDATE user_notifications
SET is_read = 1
WHERE user_id = ? AND is_read = 0;

-- Mark All Admin Notifications as Read
UPDATE admin_notifications
SET is_read = 1
WHERE admin_id = ? AND is_read = 0;

-- Mark All Head Notifications as Read
UPDATE head_notifications
SET is_read = 1
WHERE is_read = 0;

-- ==================== UNREAD COUNTS ====================

-- Get User Unread Count
SELECT COUNT(*)
FROM user_notifications
WHERE user_id = ? AND is_read = 0;

-- Get Admin Unread Count
SELECT COUNT(*)
FROM admin_notifications
WHERE admin_id = ? AND is_read = 0;

-- Get Head Unread Count
SELECT COUNT(*)
FROM head_notifications
WHERE is_read = 0;

-- ==================== DELETE NOTIFICATIONS ====================

-- Delete User Notification
DELETE FROM user_notifications
WHERE id = ? AND user_id = ?;

-- Delete Admin Notification
DELETE FROM admin_notifications
WHERE id = ? AND admin_id = ?;

-- Delete Head Notification
DELETE FROM head_notifications
WHERE id = ?;

-- Delete Old Read Notifications (cleanup - older than 30 days)
DELETE FROM user_notifications
WHERE is_read = 1 AND created_at < datetime('now', '-30 days');

DELETE FROM admin_notifications
WHERE is_read = 1 AND created_at < datetime('now', '-30 days');

DELETE FROM head_notifications
WHERE is_read = 1 AND created_at < datetime('now', '-30 days');

-- ==================== NOTIFICATION STATISTICS ====================

-- Get User Notification Statistics
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread,
    SUM(CASE WHEN is_read = 1 THEN 1 ELSE 0 END) as read,
    COUNT(DISTINCT type) as types_count
FROM user_notifications
WHERE user_id = ?;

-- Get Admin Notification Statistics
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread,
    SUM(CASE WHEN is_read = 1 THEN 1 ELSE 0 END) as read
FROM admin_notifications
WHERE admin_id = ?;

-- Get Head Notification Statistics by Type
SELECT 
    type,
    COUNT(*) as count,
    SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread
FROM head_notifications
GROUP BY type
ORDER BY count DESC;

-- Get Recent Notification Activity (last 24 hours)
SELECT 
    'user' as source,
    COUNT(*) as count
FROM user_notifications
WHERE created_at > datetime('now', '-1 day')
UNION ALL
SELECT 
    'admin' as source,
    COUNT(*) as count
FROM admin_notifications
WHERE created_at > datetime('now', '-1 day')
UNION ALL
SELECT 
    'head' as source,
    COUNT(*) as count
FROM head_notifications
WHERE created_at > datetime('now', '-1 day');

-- ==================== NOTIFICATION WITH RELATED DATA ====================

-- Get User Notifications with Complaint Details
SELECT 
    n.id,
    n.type,
    n.message,
    n.is_read,
    n.created_at,
    c.id as complaint_id,
    c.bus_number,
    c.category,
    c.status
FROM user_notifications n
LEFT JOIN complaints c ON n.related_id = c.id
WHERE n.user_id = ?
ORDER BY n.created_at DESC
LIMIT ?;

-- Get Head Notifications with User Info
SELECT 
    n.id,
    n.type,
    n.message,
    n.is_read,
    n.created_at,
    c.id as complaint_id,
    u.name as user_name,
    u.email as user_email
FROM head_notifications n
LEFT JOIN complaints c ON n.related_id = c.id
LEFT JOIN users u ON c.user_id = u.id
WHERE n.type = 'new_complaint'
ORDER BY n.created_at DESC
LIMIT ?;

-- ==================== BULK OPERATIONS ====================

-- Create Multiple User Notifications (e.g., broadcast to all users in a district)
INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
SELECT 
    u.id,
    'message',
    'System maintenance scheduled for tonight',
    NULL,
    0
FROM users u
WHERE u.role = 'user';

-- Create Notifications for Admins in Specific District
INSERT INTO admin_notifications (admin_id, sender_id, message, is_read)
SELECT 
    a.admin_id,
    ?,  -- sender_id (head)
    'New complaint in your assigned district',
    0
FROM admin_assignments a
WHERE a.district_id = ?;

-- ==================== NOTIFICATION TEMPLATES ====================

-- Template: Complaint Reply Notification
-- INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
-- VALUES (?, 'reply', CONCAT('Admin replied to your complaint #', ?), ?, 0);

-- Template: Status Change Notification
-- INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
-- VALUES (?, 'status_resolved', CONCAT('Your complaint #', ?, ' has been ', ?), ?, 0);

-- Template: New Complaint for Head
-- INSERT INTO head_notifications (type, message, related_id, is_read)
-- VALUES ('new_complaint', CONCAT('New complaint #', ?, ' from ', ?), ?, 0);

-- Template: Admin Activity
-- INSERT INTO head_notifications (type, message, related_id, is_read)
-- VALUES ('admin_activity', CONCAT('Admin ', ?, ' ', ?, ' complaint #', ?), ?, 0);

-- ==================== INDEXES FOR PERFORMANCE ====================

-- Index on user_id and is_read for fast user notification queries
CREATE INDEX IF NOT EXISTS idx_user_notifications_user_read 
ON user_notifications(user_id, is_read);

-- Index on admin_id and is_read for fast admin notification queries
CREATE INDEX IF NOT EXISTS idx_admin_notifications_admin_read 
ON admin_notifications(admin_id, is_read);

-- Index on is_read for fast head notification queries
CREATE INDEX IF NOT EXISTS idx_head_notifications_read 
ON head_notifications(is_read);

-- Index on created_at for ordering
CREATE INDEX IF NOT EXISTS idx_user_notifications_created 
ON user_notifications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_notifications_created 
ON admin_notifications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_head_notifications_created 
ON head_notifications(created_at DESC);

-- ==================== USAGE EXAMPLES ====================

/*
Example 1: User submits complaint, notify head
-------------------------------------------------
1. Complaint created with ID = 100
2. Execute:
   INSERT INTO head_notifications (type, message, related_id, is_read)
   VALUES ('new_complaint', 'New complaint #100 from user@email.com', 100, 0);
3. WebSocket emits notification to all connected heads

Example 2: Admin replies to complaint, notify user
--------------------------------------------------
1. Admin adds reply to complaint ID = 100
2. Get user_id from complaints table
3. Execute:
   INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
   VALUES (55, 'reply', 'Admin replied to your complaint #100', 100, 0);
4. WebSocket emits notification to user ID 55

Example 3: Status changed to resolved, notify user
--------------------------------------------------
1. Complaint ID = 100 status changed to 'resolved'
2. Execute:
   INSERT INTO user_notifications (user_id, type, message, related_id, is_read)
   VALUES (55, 'status_resolved', 'Your complaint #100 has been resolved', 100, 0);
3. WebSocket emits notification to user ID 55

Example 4: Head sends message to admin
--------------------------------------
1. Head (user_id = 1) sends message to admin (user_id = 25)
2. Execute:
   INSERT INTO admin_notifications (admin_id, sender_id, message, is_read)
   VALUES (25, 1, 'Please review complaint #100', 0);
3. WebSocket emits notification to admin ID 25
*/
