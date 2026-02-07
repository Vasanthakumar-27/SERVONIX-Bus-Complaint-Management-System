# Quick Start Guide - SERVONIX Refactored

## 🎯 What Changed?

**Before:** 200+ cluttered files, 5028-line monolithic app  
**After:** Clean modular structure, organized code

## 🚀 Running the Application

### Option 1: NEW Modular App (Recommended for new development)
```powershell
cd backend
python app.py
```
**Status:** ✅ Auth working, other routes TODO

### Option 2: LEGACY App (Full functionality - temporary)
```powershell
cd backend
python app_sqlite.py
```
**Status:** ✅ All features working (will be phased out)

## 📁 Where Things Are Now

```
Root (was 200+ files → now 7 files)
├── .gitignore          # NEW - Git ignore rules
├── README.md           # NEW - Project documentation  
├── package.json        # Node dependencies
├── favicon.png         # App icon
└── *.ps1              # Server scripts

/backend
├── app.py             # ✨ NEW entry point
├── config.py          # ✨ NEW configuration
├── app_sqlite.py      # LEGACY (still working)
├── routes/            # ✨ NEW modular routes
│   └── auth.py       # ✅ Authentication
├── utils/             # ✨ NEW utilities
├── services/          # ✨ NEW services
├── models/            # ✨ NEW models
└── database/          # ✨ NEW DB layer

/data                  # ✨ NEW - Databases here
├── servonix.db
└── bus_complaints.db

/docs                  # ✨ NEW - Documentation
└── MIGRATION_GUIDE.md
```

## 🔑 Key Files

| File | Purpose | Status |
|------|---------|--------|
| `backend/app.py` | NEW modular entry | ✅ Working |
| `backend/config.py` | Configuration | ✅ Working |
| `backend/routes/auth.py` | Auth routes | ✅ Complete |
| `backend/app_sqlite.py` | LEGACY app | ⚠️ Temporary |
| `README.md` | Documentation | ✅ Complete |

## 🛠️ Development Workflow

### Adding New Routes:
1. Create file in `backend/routes/`
2. Define blueprint
3. Register in `backend/app.py`

Example:
```python
# backend/routes/complaints.py
from flask import Blueprint
complaints_bp = Blueprint('complaints', __name__, url_prefix='/api')

@complaints_bp.route('/complaints', methods=['GET'])
def get_complaints():
    return {'complaints': []}
```

```python
# backend/app.py
from routes.complaints import complaints_bp
app.register_blueprint(complaints_bp)
```

## 📝 Environment Setup

Copy `.env.example` to `.env`:
```env
SECRET_KEY=your-secret-key
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

## 🗑️ What Was Deleted?

- ✅ 57 duplicate "copy" files
- ✅ 18 fix/patch scripts
- ✅ 9 test scripts from root
- ✅ 20 documentation files
- ✅ 11 backend temp files
**Total: 115 unnecessary files removed**

## ⚠️ Important Notes

1. **Databases moved to `/data`** - Never commit them
2. **Use `app.py`** for new development
3. **`app_sqlite.py` still works** - Will be removed after full migration
4. **Auth routes extracted** - Other routes coming soon

## 📊 Migration Status

```
✅ DONE (25% complete):
  - File cleanup
  - Directory structure
  - Configuration extraction
  - Auth routes blueprint
  - Documentation

🚧 IN PROGRESS:
  - Complaints routes
  - Admin routes
  - User routes
  - Service layer

⏳ TODO:
  - Complete route extraction
  - Testing suite
  - API documentation
```

## 🆘 Troubleshooting

**Database not found?**
→ Check `/data` directory exists and contains `.db` files

**Import errors?**
→ Activate virtual environment: `.venv\Scripts\activate`

**Port already in use?**
→ Kill existing Python processes or use different port

**Need full functionality?**
→ Use `app_sqlite.py` temporarily until migration completes

## 📚 Documentation

- **Project Overview:** `README.md`
- **Migration Details:** `docs/MIGRATION_GUIDE.md`
- **This Guide:** `docs/QUICK_START.md`

## 🎓 Next Steps

1. **For using current system:** Run `app_sqlite.py`
2. **For new development:** Add routes to modular structure
3. **For contributing:** Read `docs/MIGRATION_GUIDE.md`

---
**Updated:** December 16, 2025  
**Status:** Refactoring Phase 1 Complete
