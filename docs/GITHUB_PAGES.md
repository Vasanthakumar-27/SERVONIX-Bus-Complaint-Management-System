# Deploy SERVONIX Frontend to GitHub Pages

Complete guide to deploy your SERVONIX frontend to GitHub Pages (free static hosting).

---

## ⚠️ Important: Frontend vs Backend

**GitHub Pages hosts ONLY the frontend (static files):**
- ✅ HTML, CSS, JavaScript
- ✅ Images, fonts, static assets
- ❌ **Cannot host Flask backend** (needs separate deployment)

**Two scenarios:**

### Scenario 1: Frontend Only on GitHub Pages
- Frontend: GitHub Pages (FREE)
- Backend: Render/Railway/Heroku (separate deployment)

### Scenario 2: Full Local Development
- Just use for testing
- Frontend & Backend run locally

---

## 🚀 Step 1: Enable GitHub Pages

### Go to Repository Settings

1. **Open your GitHub repository:** https://github.com/USERNAME/SERVONIX
2. Click **Settings** (top right)
3. Click **Pages** (left sidebar)

### Configure GitHub Pages

1. **Under "Build and deployment":**
   - **Source:** Select `Deploy from a branch`
   - **Branch:** Select `main` 
   - **Folder:** Select `/servonix_frontend` (or `/frontend` if that's your folder)
   - Click **Save**

2. ⏳ Wait 2-3 minutes for deployment
3. You'll see:
   ```
   ✅ Your site is live at https://USERNAME.github.io/SERVONIX/
   ```

---

## 📝 Step 2: Verify Your Folder Structure

Before deploying, ensure your folder has these files:

```
SERVONIX/
├── servonix_frontend/              (or frontend/ folder)
│   ├── index.html                  ✅ Main login page
│   ├── html/
│   │   ├── user_dashboard.html
│   │   ├── admin_dashboard.html
│   │   └── ...
│   ├── js/
│   │   ├── app.js
│   │   ├── auth.js
│   │   ├── realtime.js
│   │   └── ...
│   ├── css/
│   │   ├── styles.css
│   │   ├── theme.css
│   │   └── ...
│   └── assets/
│       └── images/
```

If you don't have a `servonix_frontend` folder:
- Rename your `frontend/` folder to `servonix_frontend/`
- Or create symbolic link

---

## 🔗 Step 3: Update Base URL in Frontend

Your frontend will be at `https://USERNAME.github.io/SERVONIX/` (note the `/SERVONIX/` path).

**Update `servonix_frontend/js/app.js`:**

```javascript
// Add this at the top of app.js
const IS_GITHUB_PAGES = window.location.hostname.includes('github.io');
const BASE_PATH = IS_GITHUB_PAGES ? '/SERVONIX' : '';

// Update all fetch calls to use BASE_PATH
const API_BASE = 'http://localhost:5000/api';  // For local
// OR for deployed backend:
// const API_BASE = 'https://your-backend-url.onrender.com/api';
```

**Update all fetch calls (example):**

```javascript
// BEFORE:
fetch('/api/auth/login', { ... })

// AFTER:
fetch(`${BASE_PATH}/api/auth/login`, { ... })
```

**Or update `servonix_frontend/index.html`:**

Add this in `<head>`:
```html
<base href="/SERVONIX/">
```

---

## 🔌 Step 4: Configure Backend URL

### Option A: Local Backend (Development)

Edit `servonix_frontend/js/app.js`:

```javascript
const API_URL = 'http://localhost:5000';  // localhost backend
```

**Requirements:**
- Backend running locally on port 5000
- CORS must allow GitHub Pages origin
- Only works during local testing

### Option B: Deployed Backend (Production)

First, deploy backend to Render or Railway:

1. Follow [DEPLOYMENT.md](./DEPLOYMENT.md) - Part 2
2. Get your backend URL: `https://servonix-backend.onrender.com`
3. Update frontend:

```javascript
// servonix_frontend/js/app.js
const API_URL = 'https://servonix-backend.onrender.com';  // deployed backend
```

---

## 📤 Step 5: Commit & Push Changes

```powershell
cd V:\Documents\VS CODE\DT project\SERVONIX

# Commit changes
git add .
git commit -m "Update frontend for GitHub Pages deployment

- Configure base path for /SERVONIX/ repository
- Update API endpoints
- Ready for GitHub Pages hosting"

# Push to GitHub
git push origin main
```

⏳ **Wait 2-3 minutes** for GitHub Pages to rebuild.

---

## ✅ Step 6: Access Your Deployed Site

Visit your frontend:

```
https://USERNAME.github.io/SERVONIX/
```

**Replace `USERNAME` with your GitHub username.**

---

## 🧪 Test Deployment

### Test Frontend Access:

1. Go to `https://USERNAME.github.io/SERVONIX/`
2. You should see the **Login Page**
3. Check browser console (F12) for errors

### Test Backend Connection:

1. Open **Developer Tools** (F12)
2. Go to **Console** tab
3. You should **NOT** see CORS or connection errors
4. Try logging in with demo credentials

### Common Errors:

| Error | Cause | Fix |
|-------|-------|-----|
| 404 Not Found | Wrong folder name | Use `/servonix_frontend` |
| Page content not loading | Wrong base path | Add `<base href="/SERVONIX/">` |
| Can't login | Backend API not deployed | Deploy backend first |
| CORS error | Backend not allowing GitHub Pages origin | Update CORS in backend |

---

## 🔐 Enable Backend CORS for GitHub Pages

**Update `backend/app.py`:**

```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:*",
            "http://127.0.0.1:*",
            "https://USERNAME.github.io",  # Add this line
            "http://192.168.*.*:*",
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})
```

**Then redeploy backend** (if using Render/Railway).

---

## 🚀 Full Deployment Setup

### For Complete Deployment:

**Option 1: GitHub Pages + Render Backend (Recommended)**

1. ✅ Frontend on GitHub Pages (FREE)
2. Deploy backend to Render (Follow [DEPLOYMENT.md](./DEPLOYMENT.md))
3. Update frontend to use Render backend URL
4. Push to GitHub → Deploy

**Option 2: GitHub Pages Only (Local Backend)**

1. ✅ Frontend on GitHub Pages (FREE)
2. Keep backend running locally on port 5000
3. Frontend connects to localhost:5000
4. Only works when your computer is running

---

## 📊 GitHub Pages Dashboard

After deployment, you can monitor your site:

1. Go to **Settings** → **Pages**
2. You'll see:
   - ✅ Deployment status
   - 📊 Visit history
   - 🔗 Your live URL
   - ⚡ Last deployment time

---

## 🔄 Update & Redeploy

Any time you make changes:

```powershell
# Make changes to frontend files

# Commit & push
git add .
git commit -m "Update: [describe changes]"
git push origin main

# GitHub Pages auto-deploys (2-3 min wait)
```

---

## 🆘 Troubleshooting

### Issue: "404 - Not Found"
**Solution:** Check if folder is named correctly
```bash
# Make sure folder exists
ls servonix_frontend/
ls servonix_frontend/index.html
```

### Issue: "Page works but shows nothing"
**Solution:** Check browser console (F12 → Console)
- Look for JavaScript errors
- Check CORS errors
- Verify API URL is correct

### Issue: "Can't login - backend error"
**Solution:** 
1. Verify backend is deployed (Render/Railway)
2. Update API URL in frontend code
3. Check CORS settings in backend

### Issue: "Styles/Images not loading"
**Solution:** Make sure `<base href="/SERVONIX/">` is in HTML head

### Issue: "Real-time updates not working"
**Solution:** WebSocket may not work on GitHub Pages
- Configure backend to allow WebSocket
- Or use polling instead

---

## 💡 Tips & Best Practices

✅ **Do:**
- Keep frontend files in `/servonix_frontend` folder
- Update API URL in config file (not hardcoded)
- Test locally before pushing
- Add environment variables for different URLs

❌ **Don't:**
- Don't put backend code in GitHub Pages folder
- Don't hardcode localhost URLs
- Don't commit `.env` files with secrets
- Don't forget to enable GitHub Pages in Settings

---

## 📚 Useful Links

- [GitHub Pages Docs](https://pages.github.com/)
- [GitHub Pages Custom Domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-site)
- [GitHub Pages Troubleshooting](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)

---

## 🎯 Quick Summary

```bash
# 1. Enable GitHub Pages (Settings → Pages)
# 2. Choose main branch, /servonix_frontend folder
# 3. Update frontend API URL
# 4. Deploy backend separately (Render/Railway)
# 5. Push to GitHub
# 6. Visit https://USERNAME.github.io/SERVONIX/
```

---

**Your site is now live! 🎉**

Check [DEPLOYMENT.md](./DEPLOYMENT.md) to deploy the backend as well.
