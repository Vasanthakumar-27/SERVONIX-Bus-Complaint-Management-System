# SERVONIX - Bus Complaint Management System

## 📋 Project Overview

SERVONIX is a Flask-based complaint management system for bus transportation services with role-based access for users, admins, and heads.

## 🏗️ Architecture (Refactored - December 2025)

### **Backend Structure**
```
backend/
├── app.py                      # NEW: Main application entry (replaces app_sqlite.py)
├── config.py                   # NEW: Centralized configuration
├── app_sqlite.py               # LEGACY: Will be phased out
├── auth_sqlite.py              # Authentication logic
├── db_sqlite.py                # Database connection
├── api_districts.py            # District API (to be converted to blueprint)
├── notification_service.py     # Notification service
├── notification_api.py         # Notification API
├── pdf_generator.py            # PDF generation service
├── requirements.txt            # Python dependencies
│
├── models/                     # NEW: Data models (future)
│   └── __init__.py
│
├── routes/                     # NEW: Modular route blueprints
│   ├── __init__.py
│   ├── auth.py                 # ✅ DONE: Authentication routes
│   ├── complaints.py           # TODO: Complaint management
│   ├── admin.py                # TODO: Admin operations
│   ├── user.py                 # TODO: User operations
│   └── notifications.py        # TODO: Notification routes
│
├── services/                   # NEW: Business logic services
│   ├── __init__.py
│   ├── email_service.py        # TODO: Email operations
│   └── pdf_service.py          # TODO: PDF generation
│
├── database/                   # NEW: Database layer
│   ├── __init__.py
│   └── connection.py           # Database connection wrapper
│
├── utils/                      # NEW: Utility functions
│   ├── __init__.py
│   ├── helpers.py              # ✅ DONE: Helper functions
│   └── decorators.py           # ✅ DONE: Auth decorators
│
├── tests/                      # Test files
├── static/                     # Static assets
└── uploads/                    # User uploads
```

### **Project Root**
```
servonix/
├── backend/                    # Backend application
├── frontend/                   # Frontend files
│   ├── html/                   # HTML pages
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript
│   └── assets/                 # Images, icons
├── data/                       # ✅ NEW: Database files (gitignored)
│   ├── servonix.db
│   └── bus_complaints.db
├── docs/                       # ✅ NEW: Documentation
│   └── (future docs)
├── scripts/                    # Utility scripts
│   ├── create_snapshot.ps1
│   └── revert_changes.ps1
├── backups/                    # Backups (gitignored)
├── .gitignore                  # ✅ CREATED
├── .env                        # Environment variables (gitignored)
├── .env.example                # Environment template
└── README.md                   # ✅ THIS FILE
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   cd "v:\Documents\VS CODE\DT project\DT new"
   ```

2. **Create virtual environment**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```powershell
   # Copy .env.example to .env and configure
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run the application**
   ```powershell
   # Using new modular app
   python app.py

   # OR using legacy app (temporary)
   python app_sqlite.py
   ```

6. **Access the application**
   - Frontend: http://localhost:5000
   - API: http://localhost:5000/api/

## 📊 Database

Database files are now located in `/data` directory:
- `data/servonix.db` - Main application database
- `data/bus_complaints.db` - Complaints database

**⚠️ Never commit database files to git**

## 🔧 Configuration

Configuration is managed in `backend/config.py`:

```python
# Key settings
DATABASE_PATH       # Database location
UPLOAD_FOLDER       # File upload directory
MAX_CONTENT_LENGTH  # Max upload size (1GB)
SMTP_SERVER         # Email server
CORS_ORIGINS        # Allowed origins
```

Environment variables (`.env`):
```
SECRET_KEY=your-secret-key
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🛣️ API Routes

### Authentication (`/api`)
- `POST /register` - Register new user
- `POST /login` - User login
- `GET /profile` - Get user profile
- `POST /forgot-password` - Request password reset OTP
- `POST /verify-otp` - Verify OTP
- `POST /reset-password` - Reset password
- `POST /change-password` - Change password (authenticated)

### Complaints (TODO - in progress)
- Coming from `app_sqlite.py` extraction

### Admin (TODO - in progress)
- Coming from `app_sqlite.py` extraction

## 🧪 Testing

```powershell
# Run tests
cd backend
python -m pytest tests/
```

## 📝 Migration Status

### ✅ Completed
1. Deleted 100+ duplicate/temp files
2. Created modular directory structure
3. Moved databases to `/data`
4. Created `.gitignore`
5. Extracted configuration to `config.py`
6. Created utility modules
7. Extracted auth routes to blueprint
8. Created new `app.py` with application factory

### 🚧 In Progress
- Extracting complaint routes from `app_sqlite.py`
- Extracting admin routes from `app_sqlite.py`
- Creating service layer for email/PDF
- Converting district API to blueprint

### 📋 TODO
- Complete route extraction (app_sqlite.py is 4747 lines)
- Create data models layer
- Add comprehensive tests
- API documentation
- Deployment guide

## 🗑️ Cleanup Summary

**Deleted Files:**
- 57 duplicate 'copy' files
- 18 temporary fix scripts
- 9 test scripts from root
- 20 excessive documentation files
- 11 backend temporary files
- **Total: ~115 files removed**

**Before:** 200+ files  
**After:** ~50 core files

## 🔐 Security Notes

- Never commit `.env` file
- Never commit database files
- Never commit uploads folder
- Use environment variables for secrets
- Keep `SECRET_KEY` secure in production

## 📚 Development Guidelines

1. **New routes:** Create in `backend/routes/` as blueprints
2. **Business logic:** Place in `backend/services/`
3. **Utilities:** Add to `backend/utils/`
4. **Database:** Use `get_db()` from `database/connection`
5. **Testing:** Write tests in `backend/tests/`

## 🐛 Known Issues

- `app_sqlite.py` (4747 lines) still in use - being phased out
- Some routes not yet converted to blueprints
- Email service needs extraction

## 📞 Support

For issues or questions about the refactored architecture, check:
1. This README
2. Code comments in `app.py`
3. Individual route blueprint files

---

**Last Updated:** December 16, 2025  
**Architecture Version:** 2.0 (Modular)  
**Status:** ✅ Structure refactored, routes migration in progress
