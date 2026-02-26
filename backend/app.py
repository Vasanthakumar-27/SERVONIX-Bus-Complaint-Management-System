"""SERVONIX - Main Application Entry Point"""
import os
import sys
import logging
from urllib.parse import urlparse
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_talisman import Talisman
from flask_socketio import SocketIO
from dotenv import load_dotenv

# Load .env from backend/ directory BEFORE any other imports that read env vars
_backend_dir = os.path.dirname(__file__)
load_dotenv(os.path.join(_backend_dir, '.env'))

from .config import config
from .database.connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Ensure logs directory and file handler
try:
    logs_path = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_path, exist_ok=True)
    fh = logging.FileHandler(os.path.join(logs_path, 'app.log'))
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(fh)
except Exception:
    logger.exception('Failed to initialize file logging')


def create_app():
    """Application factory"""
    app = Flask(__name__, 
                static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'),
                static_url_path='')
    
    # Configuration
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB max upload
    
    # CORS configuration - prefer an explicit FRONTEND_URL; fallback to safe defaults
    _frontend_url = os.environ.get('FRONTEND_URL', '').strip()
    _allowed_origins = [
        "http://localhost",
        "http://127.0.0.1",
        "http://[::1]",
        r"https://.*\.github\.io",
        r"https://.*\.onrender\.com",
    ]
    
    # Extract origin (scheme + domain) from FRONTEND_URL if provided
    # CORS origins don't include paths!
    if _frontend_url:
        parsed = urlparse(_frontend_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        _allowed_origins.insert(0, origin)

    CORS(app, resources={
        r"/api/*": {
            "origins": _allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600
        },
        r"/uploads/*": {
            "origins": _allowed_origins,
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "Range"],
        }
    })
    
    # Initialize SocketIO with proper WebSocket support
    # Use eventlet async worker for production WebSocket support
    # Use same allowed origins for Socket.IO (avoid wildcard in production)
    socketio = SocketIO(
        app,
        async_mode='eventlet',
        cors_allowed_origins=_allowed_origins,
        ping_timeout=60,
        ping_interval=25,
        logger=False,
        engineio_logger=False
    )
    
    # Initialize database
    init_db()
    
    # Initialize services
    from .services.file_service import FileService
    from .services.socketio_service import SocketIOService
    from .services.notification_service import NotificationService
    from .database.connection import get_db
    
    file_service = FileService(config.UPLOAD_FOLDER)
    socketio_service = SocketIOService(socketio, get_db)
    notification_service = NotificationService()
    
    # Store services in app config
    app.config['file_service'] = file_service
    app.config['socketio_service'] = socketio_service
    app.config['notification_service'] = notification_service
    
    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.complaints import complaints_bp
    from .routes.admin import admin_bp
    from .routes.user import user_bp
    from .routes.head import head_bp
    from .routes.feedback import feedback_bp
    from .routes.messaging import messaging_bp
    from .routes.districts import districts_bp
    from .routes.dashboard import dashboard_bp
    from .routes.admin_head_messaging import admin_head_bp
    from .routes.messages import messages_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(head_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(messaging_bp)
    app.register_blueprint(districts_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_head_bp)
    app.register_blueprint(messages_bp)
    # Register debug blueprint (protected via DEBUG_API_KEY header)
    try:
        from .routes.debug import debug_bp
        app.register_blueprint(debug_bp)
        logger.info('Debug blueprint registered at /debug')
    except Exception:
        logger.exception('Failed to register debug blueprint')
    
    # Root and frontend routes — redirect browser visitors to the GitHub Pages frontend.
    # This backend is an API server; the UI is served from GitHub Pages.
    FRONTEND_HOME = os.environ.get(
        'FRONTEND_URL',
        'https://vasanthakumar-27.github.io/SERVONIX-Bus-Complaint-Management-System/'
    )

    @app.route('/')
    def index():
        """Redirect root to GitHub Pages frontend"""
        from flask import redirect
        return redirect(FRONTEND_HOME, code=302)

    @app.route('/splash')
    @app.route('/splash.html')
    @app.route('/login')
    @app.route('/login.html')
    @app.route('/register')
    @app.route('/register.html')
    @app.route('/admin_dashboard')
    @app.route('/admin_dashboard.html')
    @app.route('/head_dashboard')
    @app.route('/head_dashboard.html')
    @app.route('/user_dashboard')
    @app.route('/user_dashboard.html')
    def redirect_to_frontend():
        """Redirect all page routes to GitHub Pages frontend"""
        from flask import redirect
        return redirect(FRONTEND_HOME, code=302)
    
    # Serve other static resources
    @app.route('/frontend/<path:filename>')
    def serve_frontend(filename):
        """Serve frontend files"""
        return send_from_directory(app.static_folder, filename)
    
    @app.route('/css/<path:filename>')
    def serve_css(filename):
        """Serve CSS files"""
        return send_from_directory(os.path.join(app.static_folder, 'css'), filename)
    
    @app.route('/js/<path:filename>')
    def serve_js(filename):
        """Serve JavaScript files"""
        return send_from_directory(os.path.join(app.static_folder, 'js'), filename)
    
    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        """Serve asset files"""
        return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)
    
    @app.route('/html/<path:filename>')
    def serve_html(filename):
        """Serve HTML files"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), filename)
    
    # Serve media/uploads files
    @app.route('/api/media/<path:filename>')
    def serve_media(filename):
        """Serve uploaded media files"""
        uploads_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        return send_from_directory(uploads_folder, filename)
    
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        """Serve uploaded files (alternative route)"""
        uploads_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        return send_from_directory(uploads_folder, filename)
    
    @app.route('/static/uploads/<path:filename>')
    def serve_static_uploads(filename):
        """Serve uploaded files (backward compatibility route)"""
        uploads_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        return send_from_directory(uploads_folder, filename)
    
    # Health check
    @app.route('/api/health', methods=['GET', 'OPTIONS'])
    def health_check():
        """API health check endpoint"""
        if request.method == 'OPTIONS':
            return '', 204
        return {'status': 'healthy', 'service': 'SERVONIX API'}, 200
    
    # Add preflight handler for CORS
    @app.before_request
    def handle_preflight():
        """Handle CORS preflight requests"""
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.status_code = 200
            return response
    
    # Apply Talisman for security headers (HSTS, CSP control) and also set a few custom headers
    try:
        # Use a permissive CSP=None so we don't break existing inline scripts; projects can tighten this later
        Talisman(app, content_security_policy=None, force_https=False)
    except Exception:
        logger.exception('Failed to initialize Talisman')

    @app.after_request
    def set_security_headers(response):
        """Add additional security headers to all responses"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    
    # Store socketio instance on app for access by other modules
    app.socketio = socketio
    
    return app, socketio


def run_server(host=None, port=None):
    """Run development server. Host and port read from environment when not provided."""
    app, socketio = create_app()
    # Use env vars when available (platforms like Render provide $PORT)
    host = host or os.environ.get('HOST', '0.0.0.0')
    port = int(port or os.environ.get('PORT', os.environ.get('HTTP_PORT', 5000)))
    debug = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')
    logger.info(f"Starting SERVONIX server on {host}:{port} (debug={debug})")
    # When using Flask-SocketIO on production platforms, an async worker (eventlet/gevent)
    # is preferred. If available, SocketIO will select it automatically.
    socketio.run(app, host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
