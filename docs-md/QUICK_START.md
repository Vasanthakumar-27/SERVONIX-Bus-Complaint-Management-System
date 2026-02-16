# Quick Start Guide - SERVONIX Refactored

## ≡ƒÄ» What Changed?

**Before:** 200+ cluttered files, 5028-line monolithic app  
**After:** Clean modular structure, organized code

## ≡ƒÜÇ Running the Application

### Option 1: NEW Modular App (Recommended for new development)
```powershell
cd backend
python app.py
```
**Status:** Γ£à Auth working, other routes TODO

### Option 2: LEGACY App (Full functionality - temporary)
```powershell
cd backend
python app_sqlite.py
```
**Status:** Γ£à All features working (will be phased out)

## ≡ƒôü Where Things Are Now

```
Root (was 200+ files ΓåÆ now 7 files)
Γö£ΓöÇΓöÇ .gitignore          # NEW - Git ignore rules
Γö£ΓöÇΓöÇ README.md           # NEW - Project documentation  
Γö£ΓöÇΓöÇ package.json        # Node dependencies
Γö£ΓöÇΓöÇ favicon.png         # App icon
ΓööΓöÇΓöÇ *.ps1              # Server scripts

/backend
Γö£ΓöÇΓöÇ app.py             # Γ£¿ NEW entry point
Γö£ΓöÇΓöÇ config.py          # Γ£¿ NEW configuration
Γö£ΓöÇΓöÇ app_sqlite.py      # LEGACY (still working)
Γö£ΓöÇΓöÇ routes/            # Γ£¿ NEW modular routes
Γöé   ΓööΓöÇΓöÇ auth.py       # Γ£à Authentication
Γö£ΓöÇΓöÇ utils/             # Γ£¿ NEW utilities
Γö£ΓöÇΓöÇ services/          # Γ£¿ NEW services
Γö£ΓöÇΓöÇ models/            # Γ£¿ NEW models
ΓööΓöÇΓöÇ database/          # Γ£¿ NEW DB layer

/data                  # Γ£¿ NEW - Databases here
Γö£ΓöÇΓöÇ servonix.db
ΓööΓöÇΓöÇ bus_complaints.db

/docs                  # Γ£¿ NEW - Documentation
ΓööΓöÇΓöÇ MIGRATION_GUIDE.md
```

## ≡ƒöæ Key Files

| File | Purpose | Status |
|------|---------|--------|
| `backend/app.py` | NEW modular entry | Γ£à Working |
| `backend/config.py` | Configuration | Γ£à Working |
| `backend/routes/auth.py` | Auth routes | Γ£à Complete |
| `backend/app_sqlite.py` | LEGACY app | ΓÜá∩╕Å Temporary |
| `README.md` | Documentation | Γ£à Complete |

## ≡ƒ¢á∩╕Å Development Workflow

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

## ≡ƒô¥ Environment Setup

Copy `.env.example` to `.env`:
```env
SECRET_KEY=your-secret-key
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

## ≡ƒùæ∩╕Å What Was Deleted?

- Γ£à 57 duplicate "copy" files
- Γ£à 18 fix/patch scripts
- Γ£à 9 test scripts from root
- Γ£à 20 documentation files
- Γ£à 11 backend temp files
**Total: 115 unnecessary files removed**

## ΓÜá∩╕Å Important Notes

1. **Databases moved to `/data`** - Never commit them
2. **Use `app.py`** for new development
3. **`app_sqlite.py` still works** - Will be removed after full migration
4. **Auth routes extracted** - Other routes coming soon

## ≡ƒôè Migration Status

```
Γ£à DONE (25% complete):
  - File cleanup
  - Directory structure
  - Configuration extraction
  - Auth routes blueprint
  - Documentation

≡ƒÜº IN PROGRESS:
  - Complaints routes
  - Admin routes
  - User routes
  - Service layer

ΓÅ│ TODO:
  - Complete route extraction
  - Testing suite
  - API documentation
```

## ≡ƒåÿ Troubleshooting

**Database not found?**
ΓåÆ Check `/data` directory exists and contains `.db` files

**Import errors?**
ΓåÆ Activate virtual environment: `.venv\Scripts\activate`

**Port already in use?**
ΓåÆ Kill existing Python processes or use different port

**Need full functionality?**
ΓåÆ Use `app_sqlite.py` temporarily until migration completes

## ≡ƒôÜ Documentation

- **Project Overview:** `README.md`
- **Migration Details:** `docs/MIGRATION_GUIDE.md`
- **This Guide:** `docs/QUICK_START.md`

## ≡ƒÄô Next Steps

1. **For using current system:** Run `app_sqlite.py`
2. **For new development:** Add routes to modular structure
3. **For contributing:** Read `docs/MIGRATION_GUIDE.md`

---
**Updated:** December 16, 2025  
**Status:** Refactoring Phase 1 Complete
