# SERVONIX - GitHub Deployment Guide

Complete guide for pushing your project to GitHub and deploying the application.

---

## 📤 Part 1: Push Code to GitHub

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. **Repository name:** `SERVONIX`
3. **Description:** Bus Complaint Management System
4. Choose **Public** (for open-source) or **Private** (for private project)
5. ✅ Check "Initialize repository with README" (if new repo)
6. Click **Create repository**

### Step 2: Configure Git Locally

If you haven't set up Git on your computer:

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@github.com"
```

### Step 3: Push Existing Code to GitHub

**If this is a NEW repository (first push):**

```bash
cd v:\Documents\VS CODE\DT project\SERVONIX

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit: SERVONIX bus complaint management system"

# Add remote (replace USERNAME with your GitHub username)
git remote add origin https://github.com/USERNAME/SERVONIX.git

# Rename branch to main (GitHub standard)
git branch -M main

# Push to GitHub
git push -u origin main
```

**If repository already exists:**

```bash
cd v:\Documents\VS CODE\DT project\SERVONIX

# Check current remote
git remote -v

# Update remote if needed
git remote set-url origin https://github.com/USERNAME/SERVONIX.git

# Add changes
git add .

# Commit
git commit -m "Update documentation: Add SETUP.md and deployment guide"

# Push
git push origin main
```

### Step 4: Verify Push Success

Go to https://github.com/USERNAME/SERVONIX and verify your code appears.

---

## 🚀 Part 2: Deploying the Application

### Option A: Heroku (Free with Limitations)

**Note:** Heroku free tier ended in 2022. Use Render or Railway instead.

### ✅ Option B: Render.com (Recommended - Free Tier Available)

#### Deploy Backend to Render

1. **Go to https://render.com** and sign up with GitHub
2. Click **New +** → **Web Service**
3. **Connect your GitHub repository**
4. **Configure:**
   - Name: `SERVONIX-Backend`
   - Environment: **Python 3.10+**
   - Build Command:
     ```bash
     pip install -r backend/requirements.txt && pip install eventlet
     ```
   - Start Command:
     ```bash
     cd backend && python app.py
     ```
5. **Environment Variables:**
   ```
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   SECRET_KEY=change-this-to-random-string
   JWT_SECRET=change-this-to-random-string
   DB_NAME=bus_complaints
   ```
6. Click **Create Web Service**
7. ⏳ Wait 2-5 minutes for deployment
8. Your backend URL: `https://servonix-backend.onrender.com`

#### Deploy Frontend to Render

1. Create `render.yaml` in project root:

```yaml
services:
  - type: web
    name: SERVONIX-Frontend
    runtime: node
    buildCommand: npm install --legacy-peer-deps
    startCommand: python -m http.server 8080 --directory servonix_frontend
    envVars:
      - key: BACKEND_URL
        value: https://servonix-backend.onrender.com
```

2. Push to GitHub
3. Deploy following same process, Select Static Site
4. Frontend URL: `https://servonix-frontend.onrender.com`

---

### ✅ Option C: Railway.app (Simple & Free)

1. **Go to https://railway.app** and sign up with GitHub
2. Create new project
3. **Deploy from GitHub:**
   - Select your SERVONIX repository
   - Choose `backend/` folder as root
4. **Add environment variables** (same as above)
5. Railway auto-detects Python and deploys
6. Backend URL auto-generated

---

### ✅ Option D: Vercel (Frontend Only)

1. **Go to https://vercel.com** and sign up with GitHub
2. Click **Add New** → **Project**
3. Select your SERVONIX repository
4. **Settings:**
   - Framework: **Other**
   - Build Command: `npm install`
   - Output Directory: `servonix_frontend`
5. Click **Deploy**
6. Add environment: `VITE_API_URL=https://your-backend-url.com`

---

### ✅ Option E: GitHub Pages (Frontend Only)

1. **Enable GitHub Pages:**
   - Go to Repository Settings
   - Scroll to **Pages**
   - Source: `main` branch
   - Folder: `/ (root)`
   - Click **Save**

2. **Your frontend appears at:**
   ```
   https://USERNAME.github.io/SERVONIX
   ```

---

## 🔄 Continuous Deployment (GitHub Actions)

### Auto-Deploy on Push

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Render

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to Render
      run: |
        curl https://api.render.com/deploy/srv-${{ secrets.RENDER_SERVICE_ID }}?key=${{ secrets.RENDER_API_KEY }} \
          -X POST
```

**Setup:**
1. Get API key from Render dashboard
2. Go to GitHub Settings → Secrets
3. Add `RENDER_SERVICE_ID` and `RENDER_API_KEY`
4. Push changes - automatic deployment starts

---

## 🔧 Domain Setup (Optional)

### Connect Custom Domain

**For Render/Railway:**
1. Go to service settings
2. Add custom domain: `servonix.yourdomain.com`
3. Update DNS records with provider
4. Wait for HTTPS certificate (auto)

---

## 📊 Production Checklist

Before deploying to production:

- [ ] Change all `SECRET_KEY` values
- [ ] Change `JWT_SECRET` to random string
- [ ] Update CORS origins (remove localhost)
- [ ] Set `DEBUG = False` in production config
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS
- [ ] Set strong email credentials
- [ ] Review environment variables
- [ ] Setup database backups
- [ ] Configure logging
- [ ] Test all features after deployment

---

## 🛡️ Security for Deployment

### Update `backend/config.py`:

```python
import os
from datetime import timedelta

class ProductionConfig:
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in deployment
    JWT_SECRET = os.environ.get('JWT_SECRET')  # Must be set in deployment
    
    # Database - Use PostgreSQL in production
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # CORS - Restrict to your domain only
    CORS_ORIGINS = ["https://yourdomain.com", "https://www.yourdomain.com"]
    
    # Email
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL')
```

---

## 🚨 Troubleshooting Deployment

| Issue | Solution |
|-------|----------|
| Build fails - missing requirements | Ensure `requirements.txt` is at `backend/requirements.txt` |
| Port 5000 already in use | Platform assigns port via `PORT` env var |
| WebSocket fails | Verify platform supports WebSocket (most do) |
| Database not found | Use managed database (PostgreSQL on platform) |
| Static files 404 | Ensure `frontend/` path is correct in `app.py` |
| CORS errors | Add deployment URL to CORS origins |

---

## 📈 Monitoring & Logs

### Render Logs:
```bash
# View live logs in Render dashboard
# Settings → Logs tab
```

### Monitor Performance:
- Render: Dashboard shows CPU, Memory, Request count
- Railway: Real-time metrics
- GitHub Actions: Deployment history

---

## 🔄 Rollback if Issues

```bash
# View previous commits
git log --oneline

# Rollback to previous version
git revert <commit-hash>
git push origin main

# Deployment auto-triggers
```

---

## 💰 Cost Estimate

| Service | Free Tier | Price |
|---------|-----------|-------|
| **Render** | 750 hours/month | $7/month |
| **Railway** | $5 credit/month | Pay as you go |
| **Vercel** | Unlimited | $20/month (advanced) |
| **GitHub Pages** | ✅ Unlimited | Free |

---

## 📚 Useful Links

- [Render Documentation](https://render.com/docs)
- [Railway Documentation](https://docs.railway.app)
- [GitHub Pages Setup](https://pages.github.com)
- [GitHub Actions](https://github.com/features/actions)
- [Vercel Deployment](https://vercel.com/docs)

---

## 🎯 Next Steps

1. ✅ Push code to GitHub (Part 1)
2. ✅ Choose deployment platform (Part 2)
3. ✅ Configure environment variables
4. ✅ Deploy backend & frontend
5. ✅ Test all features on live URL
6. ✅ Setup custom domain (optional)
7. ✅ Monitor logs & performance

---

**Questions?** Check individual platform's documentation or GitHub Issues.
