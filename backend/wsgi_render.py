"""WSGI entrypoint used by Render (rootDir = backend/).

Render sets the working directory to the `backend/` folder, so imports
are done without the `backend.` prefix.
Gunicorn command: gunicorn -k eventlet -w 1 wsgi_render:app --bind 0.0.0.0:$PORT
"""
import sys
import os

# Ensure the backend directory itself is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app  # noqa: E402

app, socketio = create_app()
