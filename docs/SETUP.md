# SERVONIX - Complete Setup Guide

A comprehensive guide for new developers to set up and run SERVONIX locally.

---

## 📋 Prerequisites

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/downloads))
- **Gmail account** (for email notifications - optional for testing)
- **Text editor/IDE** (VS Code recommended)

**Supported Systems:** Windows, macOS, Linux

---

## 🚀 Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/Vasanthakumar-27/SERVONIX.git
cd SERVONIX
```

### Step 2: Create Virtual Environment

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

✅ You should see `(.venv)` at the start of your terminal prompt.

### Step 3: Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
pip install eventlet
```

**What gets installed:**
- Flask 2.0+ - Web framework
- Flask-SocketIO - Real-time WebSocket support
- Flask-CORS - Cross-origin requests
- python-dotenv - Environment variables
- reportlab - PDF generation
- And 8+ more packages

### Step 4: Configure Environment Variables

```bash
cd backend
```

**Copy the example file:**

**Windows:**
```powershell
Copy-Item .env.example .env
```

**macOS/Linux:**
```bash
cp .env.example .env
```

**Edit `.env` with your settings:**
```env
DB_NAME=bus_complaints
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

#### 📧 Getting Gmail App Password:
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or your device)
3. Click "Generate"
4. Copy the 16-character password
5. Paste it in `.env` as `EMAIL_PASSWORD`

### Step 5: Initialize Database

The database creates automatically on first run, but you can pre-initialize:

```bash
python database/migrate.py
```

This creates `data/servonix.db` with all tables.

### Step 6: Start the Backend Server

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### Step 7: (Optional) Serve Frontend with HTTP Server

**In a new terminal:**

```bash
cd ..\servonix_frontend
python -m http.server 8080
```

Or from project root:
```bash
python -m http.server 8080 --directory servonix_frontend
```

Access: **http://localhost:8080**

---

## 🌐 Access the Application

| Component | URL | Status |
|-----------|-----|--------|
| **Backend Server** | http://localhost:5000 | Flask API |
| **Frontend** | http://localhost:8080 | Web interface |
| **API Endpoints** | http://localhost:5000/api/* | 120+ routes |

---

## 🧪 Test Login Credentials (Demo)

The application comes with pre-configured test users:

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **User** | user@example.com | userpassword | File complaints, track status |
| **Admin** | admin@example.com | adminpassword | Manage assigned complaints |
| **Head Admin** | head@example.com | headpassword | Full system control |

---

## 📁 Project Structure

```
SERVONIX/
│
├── backend/                      # Flask application
│   ├── app.py                    # 🎯 Main entry point
│   ├── config.py                 # Configuration settings
│   ├── requirements.txt           # Python packages
│   ├── .env.example              # Environment template
│   │
│   ├── routes/                   # API endpoints (120+)
│   │   ├── auth.py               # Login, register, password reset
│   │   ├── complaints.py         # File & manage complaints
│   │   ├── admin.py              # Admin operations
│   │   ├── head.py               # Head admin features
│   │   ├── messaging.py          # Real-time messaging
│   │   ├── dashboard.py          # Dashboard data
│   │   └── ...
│   │
│   ├── services/                 # Business logic
│   │   ├── socketio_service.py   # WebSocket events
│   │   ├── email_service.py      # Email notifications
│   │   ├── file_service.py       # File upload/download
│   │   ├── notification_service.py
│   │   └── auto_assignment.py    # Smart routing
│   │
│   ├── database/                 # Database layer
│   │   ├── connection.py         # SQLite connection
│   │   ├── migrate.py            # Schema creation
│   │   └── *.sql                 # SQL queries
│   │
│   ├── auth/                     # Authentication
│   │   └── utils.py              # JWT & security
│   │
│   ├── utils/                    # Helper functions
│   │   ├── decorators.py         # Auth decorators
│   │   ├── helpers.py            # Utility functions
│   │   └── rate_limiting.py      # Rate limiter
│   │
│   ├── uploads/                  # User uploads
│   │   └── profile_pics/         # Profile pictures
│   │
│   └── tests/                    # Test files
│
├── servonix_frontend/            # Frontend (if separate)
│   ├── html/                     # HTML templates
│   │   ├── index.html            # Login page
│   │   ├── user_dashboard.html   # User interface
│   │   ├── admin_dashboard.html  # Admin interface
│   │   └── ...
│   │
│   ├── js/                       # JavaScript
│   │   ├── app.js                # Main logic
│   │   ├── auth.js               # Authentication
│   │   ├── realtime.js           # WebSocket client
│   │   └── ...
│   │
│   └── css/                      # Stylesheets
│       ├── styles.css            # Main styles
│       ├── theme.css             # Dark/light theme
│       └── ...
│
├── frontend/                     # Frontend (alternate location)
│   └── [similar structure]
│
├── data/                         # Databases (auto-created)
│   └── servonix.db               # SQLite database
│
├── docs/                         # Documentation
│   ├── SETUP.md                  # This file
│   ├── QUICK_START.md            # Quick reference
│   └── ...
│
├── README.md                     # Project overview
├── CONTRIBUTING.md               # Contribution guidelines
├── LICENSE                       # MIT License
└── package.json                  # Node dependencies (optional)
```

---

## ✨ Key Features to Test

After setup, try these features to verify everything works:

### 1. **Authentication**
- Logout at the login page
- Try registering a new user
- Use "Forgot Password" with email verification

### 2. **User Features**
- File a complaint with attachments
- Upload a profile picture
- Track complaint status in real-time
- Message with assigned admin

### 3. **Real-time Updates**
- Open dashboard in two browser windows
- Update complaint status in one window
- See live updates in the other window (WebSocket)

### 4. **Admin Features**
- View assigned complaints
- Update complaint status
- Send messages to users
- View performance metrics

### 5. **Head Admin Features**
- Manage all admins
- View system-wide complaints
- Bulk operations
- Generate reports

---

## 🔧 Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'flask'`
**Solution:** Install dependencies:
```bash
pip install -r backend/requirements.txt
```

### Problem: Port 5000 already in use
**Solution:** Change the port in `backend/app.py`:
```python
if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5001, debug=True)
```

### Problem: Port 8080 already in use
**Solution:** Use a different port:
```bash
python -m http.server 8081
```

### Problem: `FileNotFoundError: .env file not found`
**Solution:** Make sure you're in the `backend/` directory and created `.env`:
```bash
cd backend
cp .env.example .env
```

### Problem: WebSocket connection fails
**Solution:** Ensure eventlet is installed:
```bash
pip install eventlet
```

### Problem: Email not working
**Solution:** 
- Use Gmail App Password (not your Google password)
- Enable 2-Factor Authentication on Gmail first
- Make sure `.env` has `EMAIL_SENDER` and `EMAIL_PASSWORD` set

### Problem: Frontend not connecting to backend
**Solution:**
- Check backend is running on port 5000
- Frontend should be on a different port (8080)
- Check browser console for CORS errors
- Verify backend `CORS` settings in `app.py`

### Problem: Database file not found
**Solution:**
- Delete `data/` folder
- Run app.py again (creates fresh database)
- Database auto-initializes with demo data

---

## 🔒 Security Notes

⚠️ **For Development Only:**
- Demo credentials are hardcoded for testing
- SQLite is single-file (not production-ready)
- CORS allows all localhost IPs
- JWT secret is default

🔐 **For Production:**
1. Change all `SECRET_KEY` and `JWT_SECRET` values
2. Migrate to PostgreSQL/MySQL
3. Restrict CORS origins
4. Use environment-based secrets
5. Enable HTTPS
6. Set strong admin passwords

---

## 📚 Development Workflow

### Adding a New API Endpoint

1. **Create route in `backend/routes/`:**
```python
# backend/routes/complaints.py
from flask import Blueprint, request, jsonify
from auth.utils import token_required

complaints_bp = Blueprint('complaints', __name__, url_prefix='/api')

@complaints_bp.route('/complaints', methods=['GET'])
@token_required
def get_complaints(current_user):
    """Get all complaints for user"""
    return jsonify({'complaints': []})
```

2. **Register in `backend/app.py`:**
```python
from routes.complaints import complaints_bp
app.register_blueprint(complaints_bp)
```

3. **Handle in frontend `js/app.js`:**
```javascript
async function fetchComplaints() {
    const response = await fetch('/api/complaints', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return await response.json();
}
```

### Running Tests

```bash
pytest backend/tests/
```

---

## 🤝 Getting Help

- **Documentation:** See [docs/](../docs/) folder
- **Issues:** Check GitHub Issues
- **Discussions:** GitHub Discussions
- **Security:** See [SECURITY.md](../SECURITY.md)

---

## 📦 Dependencies Overview

**Backend (`requirements.txt`):**
- Flask 2.0+ - Web framework
- Flask-SocketIO 5.3+ - WebSocket support
- Flask-CORS 3.0+ - Cross-origin requests
- python-dotenv 0.19+ - Environment variables
- reportlab 4.0+ - PDF generation
- qrcode 7.4+ - QR code generation
- pillow 10.0+ - Image processing
- werkzeug 2.0+ - WSGI utilities

**Frontend:**
- Vanilla JavaScript (ES6+)
- HTML5
- CSS3
- Socket.IO client (WebSocket)

---

## 🎯 Next Steps

1. ✅ Clone and setup (this guide)
2. ⭐ Star the repository on GitHub
3. 📖 Read [CONTRIBUTING.md](../CONTRIBUTING.md) to contribute
4. 🐛 Report bugs via GitHub Issues
5. 🚀 Deploy to production (see DEPLOYMENT.md)

---

**Happy coding! 🚀**

For questions, check existing documentation in the `docs/` folder or create an issue on GitHub.
