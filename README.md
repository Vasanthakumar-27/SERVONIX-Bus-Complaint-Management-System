# SERVONIX - Bus Complaint Management System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)](https://flask.palletsprojects.com/)

A comprehensive **real-time bus complaint management system** with role-based access control, instant messaging, multi-tier admin management, and WebSocket-powered live updates.

## 🎯 Overview

SERVONIX enables bus users to file complaints about service issues (safety, cleanliness, route quality, etc.). The system routes complaints intelligently to district admins and head administrators, tracks resolution in real-time, and provides messaging for direct communication between users, admins, and management.

**Key Achievement:** Enterprise-grade complaint platform with 120+ API endpoints, JWT authentication, SQLite persistence, and Socket.IO real-time synchronization.

---

## ✨ Features

### For Users
- 📝 File complaints with proof attachments (photos, videos, PDFs)
- 📊 Track complaint status in real-time (pending → in-progress → resolved)
- 💬 Direct messaging with assigned admins
- 📱 Mobile-responsive dashboard with dark/light theme toggle
- 🔔 Instant notifications for status updates
- 👤 Profile management with photo upload support

### For Admins (District Level)
- 📋 View assigned complaints by district/route
- ✅ Update complaint status and add resolution notes
- 📞 Message users directly for clarification
- 📈 Performance metrics and complaint statistics
- 🔍 Search and filter complaints

### For Head Administrator (System Level)
- 👨‍💼 Manage all admins (create, edit, assign districts/routes, delete)
- 📞 Global complaint oversight and escalation management
- 📧 Bulk admin assignment and messaging features
- 📊 System-wide analytics and reporting
- 🔐 Full audit and access control

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Flask 2.0+, Python 3.10+ |
| **Database** | SQLite with WAL mode for concurrency |
| **Real-time** | Flask-SocketIO with eventlet (WebSocket + polling) |
| **Authentication** | JWT (Bearer tokens) with role-based access |
| **Email** | Gmail SMTP with App Passwords |
| **PDF Generation** | ReportLab |
| **Frontend** | Vanilla JavaScript (ES6+), HTML5, CSS3 |
| **Styling** | Responsive CSS with dark/light theme support |

---

## 🚀 Quick Start

### 📋 Prerequisites
- **Python 3.10+**
- **Git**
- **Gmail account** (optional - for email notifications)

### ⚡ 5-Minute Setup

```bash
# 1. Clone & enter directory
git clone https://github.com/Vasanthakumar-27/SERVONIX.git
cd SERVONIX

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# OR on macOS/Linux: source .venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt && pip install eventlet

# 4. Configure environment (IMPORTANT!)
cd backend
cp .env.example .env
# Edit .env with your Gmail App Password (see SETUP.md for details)

# 5. Start the server
python app.py
```

🎉 **Your app is now running on http://localhost:5000**

### 📖 Full Setup Guide

For **detailed instructions, troubleshooting, and Windows/Mac/Linux specific steps**, see [**docs/SETUP.md**](docs/SETUP.md).

### 🔐 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| User | user@example.com | userpassword |
| Admin | admin@example.com | adminpassword |
| Head Admin | head@example.com | headpassword |

---

## 📁 Project Structure

```
SERVONIX/
├── backend/
│   ├── app.py                    # Flask app creation & initialization
│   ├── config.py                 # Configuration management
│   ├── requirements.txt           # Python dependencies
│   ├── auth/                      # Authentication utilities
│   ├── routes/                    # API endpoints (120+ routes)
│   │   ├── auth.py                # Login, registration, password reset
│   │   ├── complaints.py          # Complaint CRUD & management
│   │   ├── admin.py               # Admin operations
│   │   ├── head.py                # Head admin features
│   │   ├── messaging.py           # Real-time messaging
│   │   ├── user.py                # User profile & settings
│   │   └── ...
│   ├── services/                  # Business logic
│   │   ├── socketio_service.py    # WebSocket event handlers
│   │   ├── email_service.py       # Notification emails
│   │   ├── file_service.py        # File upload & management
│   │   └── auto_assignment.py     # Smart complaint routing
│   ├── database/
│   │   ├── connection.py          # SQLite connection & pooling
│   │   ├── migrate.py             # Database schema setup
│   │   └── *.sql                  # Schema & queries
│   ├── uploads/                   # User-uploaded files
│   └── static/                    # Frontend assets
│
├── frontend/
│   ├── html/                      # Dashboard pages
│   │   ├── login.html             # Authentication UI
│   │   ├── user_dashboard.html    # User complaint form & tracking
│   │   ├── admin_dashboard.html   # Admin complaint management
│   │   ├── head_dashboard.html    # Head admin system management
│   │   └── ...
│   ├── js/                        # JavaScript logic
│   │   ├── app.js                 # Entry point
│   │   ├── auth.js                # Login & auth flows
│   │   ├── dashboard.js           # Admin dashboard interactions
│   │   ├── head_dashboard.js      # Head admin features (6300+ lines)
│   │   └── realtime.js            # Socket.IO client setup
│   └── css/                       # Responsive styling
│       ├── styles.css
│       ├── dashboard.css
│       └── theme.css
│
├── docs/                          # Comprehensive documentation
│   ├── QUICK_START.md
│   ├── MESSAGING_QUICK_START.md
│   ├── PDF_GENERATION_SYSTEM.md
│   └── ...
│
├── data/                          # SQLite database (git-ignored)
├── .gitignore                     # Security: hides .env, data/, uploads/
├── package.json                   # Frontend dependencies
└── README.md                      # Project documentation
```

---

## 🔐 Authentication & Authorization

### Role-Based Access Control (RBAC)
- **User**: File complaints, track status, message admins
- **Admin**: Manage assigned complaints, respond to users
- **Head Admin**: Full system control, admin management, global oversight

### Security Features
- ✅ JWT Bearer tokens with expiration
- ✅ Password hashing (Werkzeug)
- ✅ Rate limiting on login attempts
- ✅ OTP-based password reset
- ✅ CORS configured for development/production
- ✅ `.gitignore` protects `.env` and databases from accidental git commits

---

## 🌐 API Highlights

### Authentication
```
POST   /api/auth/login              # User login
POST   /api/auth/register           # New user registration
POST   /api/auth/reset-password     # Password reset flow
```

### Complaints
```
POST   /api/complaints              # File new complaint
GET    /api/complaints              # List all complaints
GET    /api/complaints/<id>         # View complaint details
PUT    /api/complaints/<id>         # Update complaint (admin)
DELETE /api/complaints/<id>         # Delete complaint
POST   /api/complaints/<id>/messages # Add message to complaint
```

### Admin Management (Head Only)
```
GET    /api/head/admins             # List all admins
POST   /api/head/admins             # Create admin
PUT    /api/head/admins/<id>        # Edit admin details
DELETE /api/head/admins/<id>        # Delete admin
POST   /api/head/complaints/<id>/assign  # Assign complaint
```

### Real-Time (Socket.IO)
```
Events: complaint_update, message_received, status_change
Transports: WebSocket (primary), Long-polling (fallback)
```

---

## 💬 Real-Time Messaging

SERVONIX uses **Socket.IO with eventlet** for instant communication:

- **Instant notifications** when complaint status changes
- **Live messaging** between users and admins
- **Real-time dashboard updates** without page refresh
- **Automatic fallback** to long-polling if WebSocket unavailable

---

## 📸 Key Features in Action

### User Complaint Filing
- Multi-step form with category, bus number, route, description
- Proof upload (photos, videos, PDFs)
- Automatic routing to relevant district admin
- Instant confirmation and tracking number

### Admin Dashboard
- Real-time complaint list with filtering
- Status-based color coding (pending/in-progress/resolved)
- Quick-view modals with full complaint details
- Direct messaging interface with notification badges

### Head Admin Panel
- **Admin Management**: Create, edit, delete admins with district/route assignments
- **Photo Upload**: Admin profile pictures with lazy-loading
- **Bulk Operations**: Assign multiple complaints or admins
- **System Analytics**: Complaint trends, admin performance, escalation metrics

---

## 🔧 Configuration

### Environment Variables (`.env`)
```env
# Core
SECRET_KEY=your-secret-key-here
FRONTEND_URL=https://vasanthakumar-27.github.io/SERVONIX-Bus-Complaint-Management-System

# Email/SMTP (Gmail App Password - see instructions below)
EMAIL_SENDER=servonix70@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Debug (optional)
DEBUG_API_KEY=your-debug-key-here
DEBUG=false
```

### Gmail App Password Setup
1. Go to: https://myaccount.google.com/apppasswords
2. Sign in with your Gmail account
3. Create a new app password:
   - Select **Mail** from dropdown
   - Select **Other** (custom name)
   - Name it "SERVONIX SMTP"
4. Click **Generate**
5. Copy the 16-character password (format: `xxxx-xxxx-xxxx-xxxx`)
6. Use this password for `EMAIL_PASSWORD` (remove spaces)

**Note:** Regular Gmail passwords won't work. You MUST use an App Password.

### Database Files (Auto-Created)
- `data/servonix.db` — SQLite database
- `backend/uploads/` — User-uploaded files (photos, documents)

---

## 🐛 Troubleshooting

### WebSocket "Invalid frame header" error
**Solution**: Install eventlet for WebSocket support:
```bash
pip install eventlet
```

### Port 5000 already in use
```bash
# Windows: Kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -ti:5000 | xargs kill -9
```

### Database locked errors
Ensure only one instance of `app.py` is running. The database uses WAL mode for better concurrency.

### Images/files returning 404
Clear browser cache (Ctrl+F5) to reload JavaScript with updated API paths.

---

## 📊 Testing

Run the WebSocket connectivity test:
```bash
python test_websocket.py
```

This verifies:
- API health check
- JWT authentication
- Dashboard page loading
- WebSocket initialization

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 📧 Contact & Support

- **Author**: Vasanthakumar
- **Email**: 927624bad117@mkce.ac.in
- **GitHub**: [@Vasanthakumar-27](https://github.com/Vasanthakumar-27)

For issues, feature requests, or questions:
1. Check [Documentation](docs/)
2. Open a [GitHub Issue](https://github.com/Vasanthakumar-27/SERVONIX/issues)
3. Email: 927624bad117@mkce.ac.in

---

## 🎓 Acknowledgments

Built with:
- Flask & Python community
- Socket.IO for real-time capabilities
- SQLite for lightweight persistence
- Open-source libraries and best practices

---

## 📈 Future Enhancements

- [ ] Dashboard analytics with charts (Chart.js)
- [ ] SMS notifications (Twilio integration)
- [ ] Mobile app (React Native)
- [ ] Advanced reporting & export (Excel, PDF)
- [ ] Complaint escalation workflows
- [ ] AI-based auto-categorization
- [ ] Multi-language support (i18n)

---

**⭐ If you find this project useful, please star the repository!**

---

*Last updated: February 7, 2026*
*SERVONIX v1.0 - Production Ready*

---

## Debugging & SMTP

Short instructions to debug OTP/email delivery and enable production SMTP.

- **View service health** (local or deployed):

```bash
# Local health check
curl -sS http://localhost:5000/api/health

# Deployed (Render)
curl -sS https://servonix-bus-complaint-management-system.onrender.com/api/health
```

- **Use the protected debug endpoint** `/debug/status` to inspect DB objects and the recent development email log. Set a `DEBUG_API_KEY` environment variable on the server and call with header `X-DEBUG-KEY`:

```bash
curl -H "X-DEBUG-KEY: $DEBUG_API_KEY" \
	https://servonix-bus-complaint-management-system.onrender.com/debug/status
```

- **Dev email log (when SMTP not configured)**:
	- Dev emails (OTPs) are appended to `backend/logs/email_dev.log` and also printed to server logs. On Render or Docker, check that file or view service logs.

- **Enable production email (SMTP with Gmail)**:
	1. Get Gmail App Password: https://myaccount.google.com/apppasswords
	2. Add these environment variables to Render:

```env
EMAIL_SENDER=servonix70@gmail.com
EMAIL_PASSWORD=<16-char-app-password-no-spaces>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

 3. Click "Save rebuild and deploy" in Render dashboard
 4. Wait 2-5 minutes for deployment to complete
 5. Trigger an OTP (register new account via frontend) and verify email delivery

- **Common checks if OTP not received**:
	- Verify `EMAIL_PASSWORD` is the 16-character Gmail App Password (not regular password)
	- Remove spaces/dashes from app password when entering in Render
	- Check spam/junk folder in recipient's inbox
	- Gmail has daily sending limits for new accounts (wait 24h or verify account)
	- Inspect Render logs for SMTP connection errors (Dashboard → Logs tab)
	- Ensure `EMAIL_SENDER` matches the Gmail account that created the app password

**Render Deployment:** See [docs/DEPLOYMENT_STATUS.md](docs/DEPLOYMENT_STATUS.md) for complete setup checklist.
