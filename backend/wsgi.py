"""WSGI entrypoint for SERVONIX backend.

Flask-SocketIO with the eventlet worker patches the WSGI layer automatically,
so we only need to expose the plain Flask `app` object. Gunicorn is started
with:  gunicorn -k eventlet -w 1 backend.wsgi:app
"""
import sys
import os

# Ensure backend package is importable when running from repo root (/app)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app import create_app  # noqa: E402

app, socketio = create_app()
