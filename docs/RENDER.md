Render deploy checklist

This doc explains how to configure Render to run the backend and enable production email OTPs.

1) Create Render service (Web Service)
   - Connect to this GitHub repository, choose branch `main`.
   - Root Directory: `backend`
   - Start Command: `gunicorn -k gevent -w 1 backend.wsgi:app`
   - Environment: Python 3

2) Add required Secrets / Environment Variables on Render
   - `SECRET_KEY` (string)
   - `FRONTEND_URL` (full URL of your frontend, e.g. https://your-gh-pages.github.io/RepoName)
   - Email (for production)
     - `EMAIL_SENDER` (email address)
     - `EMAIL_PASSWORD` (SMTP password / app password)
     - `SMTP_SERVER` (e.g. smtp.gmail.com)
     - `SMTP_PORT` (usually 587)
   - Debug / admin
     - `DEBUG_API_KEY` (long random string to protect `/debug/status`)
     - `DEBUG` (optional boolean)

3) Optional: Render service id & API key for CI-driven deploys
   - Create a Render API Key in Render dashboard (Account -> API Keys).
   - Note the Service ID for your service (Settings -> Service ID)
   - Add these as GitHub repository secrets:
     - `RENDER_API_KEY`
     - `RENDER_SERVICE_ID`
     - `CR_PAT` (GitHub Personal Access Token with `write:packages` to push GHCR)

4) After setting env vars, redeploy from Render dashboard or use the GitHub Action `Deploy to Render` (manual dispatch).

5) Verify deployment
   - Health: `GET https://<your-render-url>/api/health` should return JSON {"service":"SERVONIX API","status":"healthy"}
   - Debug endpoint: `GET /debug/status` with header `X-DEBUG-KEY: <DEBUG_API_KEY>` to inspect DB objects and recent dev email log tail.
   - Email: Trigger a registration flow and watch logs or `backend/logs/email_dev.log` if SMTP not configured.

6) Troubleshooting hints
   - 502 / Bad Gateway: check Render logs for worker boot errors, missing modules, or database file access problems.
   - SQLite: ensure `data/.gitkeep` exists or `data/` is created at runtime; we already create `/app/data` in Dockerfile and init_db ensures directories exist.
   - Missing packages: confirm `backend/requirements.txt` is used and updated.

If you want, I can prepare a small script to call the Render API to set env vars automatically (requires `RENDER_API_KEY`).
