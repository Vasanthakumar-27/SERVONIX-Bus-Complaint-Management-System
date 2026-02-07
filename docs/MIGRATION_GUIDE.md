# Migration Guide - app_sqlite.py → Modular Architecture

## ✅ COMPLETED STEPS

### 1. File Cleanup (115 files deleted)
- ✅ Removed all `*copy.*` duplicate files (57 files)
- ✅ Removed fix/patch scripts (18 files)
- ✅ Removed test scripts from root (9 files)
- ✅ Removed excessive documentation (20 files)
- ✅ Cleaned backend directory (11 files)

### 2. Directory Restructuring
```
✅ Created /docs
✅ Created /data
✅ Created backend/models
✅ Created backend/routes
✅ Created backend/services
✅ Created backend/database
✅ Created backend/utils
✅ Moved *.db files to /data
```

### 3. New Files Created
- ✅ `.gitignore` - Comprehensive ignore rules
- ✅ `backend/config.py` - Centralized configuration
- ✅ `backend/app.py` - New modular entry point
- ✅ `backend/utils/helpers.py` - Utility functions
- ✅ `backend/utils/decorators.py` - Auth decorators
- ✅ `backend/routes/auth.py` - Authentication blueprint
- ✅ `backend/database/connection.py` - DB wrapper
- ✅ `README.md` - Project documentation

### 4. Modified Files
- ✅ `backend/db_sqlite.py` - Updated DB path to `/data`

## 🚧 IN PROGRESS

### Route Extraction from app_sqlite.py

**app_sqlite.py Analysis:**
- Total lines: 4,747
- Routes to extract: 100+
- Functions to organize: 50+

### Routes to Extract:

#### 📝 **Complaints Routes** (Priority 1)
```python
# File: backend/routes/complaints.py (TO CREATE)

@app.route('/api/complaints', methods=['GET', 'POST'])
@app.route('/api/complaints/<int:complaint_id>', methods=['GET', 'PUT', 'DELETE'])
@app.route('/api/user/complaints', methods=['GET'])
@app.route('/api/admin/complaints', methods=['GET'])
@app.route('/api/head/complaints', methods=['GET'])
@app.route('/api/complaints/<int:complaint_id>/status', methods=['PUT'])
@app.route('/api/complaints/<int:complaint_id>/resolve', methods=['PUT'])
# ... ~20 more complaint endpoints
```

#### 👥 **User Routes** (Priority 2)
```python
# File: backend/routes/user.py (TO CREATE)

@app.route('/api/user/profile-picture', methods=['POST'])
@app.route('/api/user/change-password', methods=['POST'])
@app.route('/api/user/notifications', methods=['GET'])
@app.route('/api/user/feedback', methods=['POST', 'GET'])
# ... ~10 more user endpoints
```

#### 🛡️ **Admin Routes** (Priority 3)
```python
# File: backend/routes/admin.py (TO CREATE)

@app.route('/api/admin/forward-complaint/<int:complaint_id>', methods=['POST'])
@app.route('/api/admin/notifications', methods=['GET'])
@app.route('/api/admin/reports', methods=['GET'])
@app.route('/api/admin/districts', methods=['GET'])
@app.route('/api/admin/routes', methods=['GET'])
# ... ~25 more admin endpoints
```

#### 👔 **Head Routes** (Priority 4)
```python
# File: backend/routes/head.py (TO CREATE)

@app.route('/api/head/create-admin', methods=['POST'])
@app.route('/api/head/admins', methods=['GET'])
@app.route('/api/head/admin/<int:admin_id>/toggle', methods=['PUT'])
@app.route('/api/head/admin/<int:admin_id>', methods=['DELETE'])
@app.route('/api/head/admin/<int:admin_id>/message', methods=['POST'])
@app.route('/api/head/force-logout-admins', methods=['POST'])
# ... ~15 more head endpoints
```

#### 🔔 **Notifications** (Priority 5)
```python
# File: backend/routes/notifications.py (TO CREATE)
# (Some already in notification_api.py)

@app.route('/api/notifications', methods=['GET'])
@app.route('/api/notifications/<int:id>/read', methods=['PUT'])
@app.route('/api/notifications/mark-read', methods=['PUT'])
# ... integrate with existing notification_api.py
```

#### 📊 **Reports/PDF** (Priority 6)
```python
# File: backend/routes/reports.py (TO CREATE)

@app.route('/api/reports/admin', methods=['GET'])
@app.route('/api/reports/complaints', methods=['GET'])
@app.route('/api/reports/users', methods=['GET'])
@app.route('/api/pdf/generate', methods=['POST'])
# ... ~5 report endpoints
```

## 📋 TODO LIST

### Phase 1: Extract Complaints Routes (NEXT)
- [ ] Create `backend/routes/complaints.py`
- [ ] Extract all `/api/complaints/*` routes
- [ ] Extract complaint submission logic
- [ ] Extract complaint status updates
- [ ] Test complaint endpoints
- [ ] Register blueprint in `app.py`

### Phase 2: Extract User Routes
- [ ] Create `backend/routes/user.py`
- [ ] Extract `/api/user/*` routes
- [ ] Extract profile management
- [ ] Extract user feedback
- [ ] Test user endpoints
- [ ] Register blueprint in `app.py`

### Phase 3: Extract Admin Routes
- [ ] Create `backend/routes/admin.py`
- [ ] Extract `/api/admin/*` routes
- [ ] Extract admin complaint management
- [ ] Extract admin reports
- [ ] Test admin endpoints
- [ ] Register blueprint in `app.py`

### Phase 4: Extract Head Routes
- [ ] Create `backend/routes/head.py`
- [ ] Extract `/api/head/*` routes
- [ ] Extract admin creation/management
- [ ] Extract head dashboard logic
- [ ] Test head endpoints
- [ ] Register blueprint in `app.py`

### Phase 5: Service Layer
- [ ] Create `backend/services/email_service.py`
- [ ] Extract email sending logic from routes
- [ ] Create `backend/services/pdf_service.py`
- [ ] Extract PDF generation from routes
- [ ] Create `backend/services/file_service.py`
- [ ] Extract file upload logic

### Phase 6: Testing & Documentation
- [ ] Write unit tests for all routes
- [ ] Write integration tests
- [ ] Document all API endpoints
- [ ] Create API.md documentation
- [ ] Update README with examples

### Phase 7: Deprecation
- [ ] Rename `app_sqlite.py` → `app_sqlite_LEGACY.py`
- [ ] Add deprecation warnings
- [ ] Test all functionality with new `app.py`
- [ ] Remove `app_sqlite_LEGACY.py` after verification

## 🎯 Success Criteria

✅ **Structure Complete** (DONE)
- Proper directory organization
- Configuration externalized
- Utilities modularized

🚧 **Route Migration** (IN PROGRESS)
- All routes extracted to blueprints
- app_sqlite.py < 100 lines (just imports/legacy warning)
- All endpoints tested and working

⏳ **Service Layer** (PENDING)
- Email service separated
- PDF service separated
- File service separated

⏳ **Documentation** (PENDING)
- README complete
- API documentation
- Development guide

## 🔧 How to Continue

### Run Current Code:
```powershell
cd backend

# Option 1: Use NEW modular app (auth only for now)
python app.py

# Option 2: Use LEGACY monolithic app (full functionality)
python app_sqlite.py
```

### Next Steps for Developer:
1. **Extract complaints routes:**
   - Copy complaint route handlers from app_sqlite.py
   - Create backend/routes/complaints.py
   - Register blueprint in app.py
   - Test endpoints

2. **Repeat for each route category**
3. **Gradually phase out app_sqlite.py**

## 📊 Progress Metrics

| Task | Status | Files | Lines |
|------|--------|-------|-------|
| File Cleanup | ✅ Done | -115 | -5000+ |
| Directory Structure | ✅ Done | +7 dirs | - |
| Config/Utils | ✅ Done | +5 files | +400 |
| Auth Routes | ✅ Done | +1 | +200 |
| Complaints Routes | ⏳ TODO | - | ~800 |
| Admin Routes | ⏳ TODO | - | ~600 |
| User Routes | ⏳ TODO | - | ~400 |
| Head Routes | ⏳ TODO | - | ~500 |
| Service Layer | ⏳ TODO | - | ~300 |
| Testing | ⏳ TODO | - | ~1000 |

**Total Progress: ~25% Complete**

---

**Last Updated:** December 16, 2025
**Next Milestone:** Extract complaints routes blueprint
