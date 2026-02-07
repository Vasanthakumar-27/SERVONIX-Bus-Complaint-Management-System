# 📸 Visual Demo Guide - Admin-Head Messaging System

## How to Test the Messaging System

Follow these steps to test the complete messaging workflow.

---

## 🎬 Demo Scenario: "Route 45 Bus Delay Issue"

### **Act 1: Admin Sends Message**

#### Step 1: Login as Admin
```
URL: http://127.0.0.1:5000/login
Username: admin@example.com
Password: [your admin password]
```

#### Step 2: Access Messages
1. Look at **controls bar** (below header)
2. Find button: **[🔔 Messages]**
3. Click it

**What you should see:**
- Messages section appears
- Shows "Messages to Head" title
- Blue "Compose Message" button visible
- Empty state: "No messages yet"

---

#### Step 3: Compose Message
1. Click **"Compose Message"** button
2. Modal appears with form

**Fill in the form:**
```
Subject: Urgent: Route 45 Bus Delays

Message:
We've received 5 complaints today about Route 45 buses 
being 15-30 minutes late during morning rush hour. 
Commuters are arriving late to work and are very frustrated.

This needs immediate attention.

Link Complaint: [Select Complaint #CMP-2024-00123 from dropdown]
```

3. Watch character counter update: `X/5000 characters`
4. Click **"Send Message"**

**What you should see:**
- Green toast: "✅ Message sent successfully!"
- Modal closes automatically
- Message appears in sent list with **yellow "Pending"** badge

---

### **Act 2: Head Receives & Reads**

#### Step 4: Login as Head
```
URL: http://127.0.0.1:5000/login
Username: head@example.com
Password: [your head password]
```

#### Step 5: Check Notification
1. Look at **top-right notification bar**
2. Find **envelope icon (✉️)**
3. **Red badge should show: "1"**

**What you should see:**
- Mail icon has red badge with number
- Badge pulses (animation)

---

#### Step 6: View Message in Dropdown
1. Click **envelope icon (✉️)**
2. Dropdown opens

**What you should see:**
- Message preview showing:
  - "Urgent: Route 45 Bus Delays"
  - "From: Admin Name • Feb 1, 2026"
- "View All Messages" link at bottom

---

#### Step 7: Open Full Inbox
1. Click **"View All Messages"**
2. Full-page inbox opens

**What you should see:**
- Large header: "📥 Messages from Admins"
- Filter buttons: [All Messages] [Unread] [Read] [Resolved]
- Message card showing:
  - Subject in bold
  - First 2 lines of message
  - Admin name, date, complaint link
  - **Blue "● Unread"** badge on right

---

#### Step 8: Read Message Details
1. Click the message card
2. Detail modal opens

**What you should see:**
- Full subject as heading
- Sender info: "From: Admin Name (admin@example.com)"
- Complete message text in blue box
- Yellow box showing: "🔗 Linked Complaint: #CMP-2024-00123"
- Empty reply textarea
- Buttons: [Send Reply] [Mark Resolved] [Close]

**Notice:** Message automatically marked as "Read" (badge changes to green)

---

### **Act 3: Head Replies**

#### Step 9: Send Reply
**Type in reply textarea:**
```
I've reviewed the situation. I'm assigning 2 additional 
buses to Route 45 during peak hours (7-9 AM).

The operations team will implement this starting tomorrow 
morning. I'll monitor the situation closely.

Please keep me updated if delays continue.
```

1. Click **"Send Reply"** button

**What you should see:**
- Green toast: "✅ Reply sent successfully!"
- Modal closes
- Message status changes to "Read" (if not marking resolved)

---

#### Step 10: Mark Resolved (Optional)
1. Reopen message
2. Click **"Mark Resolved"** button

**What you should see:**
- Green toast: "✅ Message marked as resolved"
- Badge changes to **gray "✓ Resolved"**

---

### **Act 4: Admin Checks Reply**

#### Step 11: Return to Admin Dashboard
1. Switch back to admin account
2. Click **"Messages"** button

**What you should see:**
- Message now has **green "Replied"** badge
- (Or gray "Resolved" if Head marked it)

---

#### Step 12: View Head's Reply
1. Click the message card
2. View modal opens

**What you should see:**
- Your original message in blue box
- Linked complaint in yellow box
- **Green box below showing:**
  - "💬 Head's Reply:"
  - Full reply text
  - Timestamp

**Perfect!** ✅ Complete conversation thread visible

---

## 🎯 Testing Checklist

### **Admin Tests**
- [ ] Messages button appears and works
- [ ] Compose modal opens with all fields
- [ ] Character counter updates correctly
- [ ] Complaint dropdown loads options
- [ ] Send message shows success toast
- [ ] Message appears in sent list
- [ ] Status badge shows "Pending" → "Replied"
- [ ] View message shows Head's reply
- [ ] Theme switching works (light/dark)

### **Head Tests**
- [ ] Mail icon shows unread badge
- [ ] Badge count is accurate
- [ ] Dropdown shows message preview
- [ ] "View All Messages" opens inbox
- [ ] Filter buttons work (All/Unread/Read/Resolved)
- [ ] Clicking message opens detail
- [ ] Message auto-marks as "Read"
- [ ] Reply textarea accepts input
- [ ] Send reply works and shows toast
- [ ] Mark resolved changes status
- [ ] Theme switching works

---

## 🐛 What to Look For (QA)

### **Bugs to Check:**
❌ **Character counter not updating** → Check textarea `oninput` event  
❌ **Badge stuck at 0** → Check API endpoint `/api/messages/head/unread-count`  
❌ **Modal won't close** → Check `onclick` handlers  
❌ **Messages not loading** → Check browser console for 401/500 errors  
❌ **Reply button disabled** → Check textarea has content  
❌ **Status not updating** → Check database writes  
❌ **Theme broken** → Check CSS variable overrides  

### **Edge Cases:**
🔍 **Very long subject** (200+ chars) → Should be rejected  
🔍 **Very long message** (5000+ chars) → Should be rejected  
🔍 **Empty message** → Should show validation error  
🔍 **Deleted complaint link** → Should show "N/A"  
🔍 **Concurrent access** → Multiple admins/heads at once  
🔍 **Expired token** → Should redirect to login  

---

## 📊 Expected Results

### **After Sending 1 Message:**

**Database:**
```sql
SELECT * FROM admin_head_messages;
```
Should show:
```
id=1, admin_id=X, head_id=Y, subject="Urgent: Route 45...", 
status="unread", created_at=[timestamp], reply_content=NULL
```

**Admin Dashboard:**
- 1 message in sent list
- Status: "Pending" (yellow badge)

**Head Dashboard:**
- Badge count: 1
- Dropdown: 1 message preview
- Inbox: 1 unread message

---

### **After Head Replies:**

**Database:**
```sql
SELECT * FROM admin_head_messages WHERE id=1;
```
Should show:
```
status="read", reply_content="I've reviewed...", 
replied_at=[timestamp], read_at=[timestamp]
```

**Admin Dashboard:**
- Status changed to "Replied" (green badge)
- View message shows reply in green box

**Head Dashboard:**
- Badge count: 0 (if no other unread)
- Message shows in "Read" filter
- Reply visible in detail modal

---

### **After Marking Resolved:**

**Database:**
```sql
SELECT * FROM admin_head_messages WHERE id=1;
```
Should show:
```
status="resolved", resolved_at=[timestamp]
```

**Admin Dashboard:**
- Status: "Resolved" (gray badge)

**Head Dashboard:**
- Message shows in "Resolved" filter
- Badge: "✓ Resolved"

---

## 🎥 Video Demo Script

If recording a demo video:

**[00:00-00:15] Introduction**
"Today I'll demonstrate the new Admin-Head messaging system..."

**[00:15-01:00] Admin Workflow**
1. Login as admin
2. Click Messages button
3. Compose message with complaint link
4. Send and show success

**[01:00-02:00] Head Workflow**
1. Login as head
2. Show badge notification
3. Open dropdown preview
4. View full inbox
5. Open message detail
6. Send reply

**[02:00-02:30] Admin Views Reply**
1. Return to admin
2. Show status changed
3. View reply

**[02:30-03:00] Head Marks Resolved**
1. Return to head
2. Mark message resolved
3. Show status update

**[03:00-03:15] Conclusion**
"Complete conversation tracked, no external tools needed!"

---

## 📸 Screenshot Checklist

Take screenshots of:

1. **Admin Compose Modal** (empty form)
2. **Admin Compose Modal** (filled form with character count)
3. **Admin Sent Messages** (with pending badge)
4. **Head Mail Badge** (showing unread count)
5. **Head Mail Dropdown** (with message preview)
6. **Head Inbox** (with filter buttons)
7. **Head Message Detail** (unread message)
8. **Head Reply Form** (with textarea)
9. **Admin View Reply** (green box with reply)
10. **Message Status Badges** (pending, replied, resolved)

---

## 🚦 Success Indicators

### **System is Working When:**

✅ Admin sends message → Database entry created  
✅ Head sees badge → Badge count matches unread  
✅ Head opens message → Status changes to "read"  
✅ Head replies → Reply stored and visible to admin  
✅ Head resolves → Status changes to "resolved"  
✅ No console errors → All API calls succeed  
✅ Theme switching → UI updates correctly  
✅ Refresh page → Messages persist  

---

## 🎓 Pro Testing Tips

### **For Thorough Testing:**

1. **Test with 10+ messages** → Check pagination/scrolling
2. **Test with long text** → Check text overflow handling
3. **Test rapid clicking** → Check for race conditions
4. **Test network errors** → Disconnect WiFi, check error handling
5. **Test expired tokens** → Wait 24 hours, check redirect
6. **Test concurrent users** → Two browsers, same time
7. **Test mobile view** → Use Chrome DevTools responsive mode
8. **Test slow network** → Use Chrome throttling

### **Performance Benchmarks:**

- **Message send:** < 500ms
- **Inbox load:** < 1 second (100 messages)
- **Badge update:** 3-second interval
- **Modal open:** < 100ms
- **Search/filter:** < 200ms

---

## 🎉 When Everything Works...

You should be able to:

1. **Send** a message from admin in **< 30 seconds**
2. **Receive** notification on head dashboard **instantly**
3. **Reply** from head in **< 1 minute**
4. **View** reply on admin dashboard **immediately**
5. **Track** entire conversation **permanently**

**That's it! Professional internal communication achieved! 🚀**

---

**Need Help?** Refer to:
- [Full Documentation](./ADMIN_HEAD_MESSAGING_SYSTEM.md)
- [Quick Start Guide](./MESSAGING_QUICK_START.md)
- [Implementation Complete](./MESSAGING_IMPLEMENTATION_COMPLETE.md)
