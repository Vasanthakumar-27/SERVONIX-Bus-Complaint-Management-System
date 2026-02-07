-- Admin-Head Messages Communication System
-- This table stores secure internal messages between Admin and Head

CREATE TABLE IF NOT EXISTS admin_head_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    head_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    message_content TEXT NOT NULL,
    complaint_id INTEGER,
    status TEXT NOT NULL DEFAULT 'unread',
    reply_content TEXT,
    replied_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME,
    resolved_at DATETIME,
    
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (head_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE SET NULL,
    
    CHECK (status IN ('unread', 'read', 'resolved'))
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_messages_head_id ON admin_head_messages(head_id, status);
CREATE INDEX IF NOT EXISTS idx_messages_admin_id ON admin_head_messages(admin_id);
CREATE INDEX IF NOT EXISTS idx_messages_complaint_id ON admin_head_messages(complaint_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON admin_head_messages(created_at DESC);
