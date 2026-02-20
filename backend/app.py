"""SERVONIX - Main Application Entry Point"""
import os
import sys
import logging
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from database.connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory"""
    app = Flask(__name__, 
                static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'),
                static_url_path='')
    
    # Configuration
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB max upload
    
    # CORS configuration - Allow localhost, local network, GitHub Pages, and Render
    _frontend_url = os.environ.get('FRONTEND_URL', '')
    _allowed_origins = [
        "http://localhost:*",
        "http://127.0.0.1:*",
        "http://192.168.*.*:*",
        "http://10.*.*.*:*",
        r"https://.*\.onrender\.com",      # any Render preview/deploy URL
        r"https://.*\.github\.io",         # any GitHub Pages URL
    ]
    if _frontend_url:
        _allowed_origins.append(_frontend_url)

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
    # Use gevent async worker (Gunicorn + gevent recommended for production).
    socketio = SocketIO(
        app,
        async_mode='gevent',
        cors_allowed_origins="*",
        ping_timeout=60,
        ping_interval=25,
        logger=False,
        engineio_logger=False
    )
    
    # Initialize database
    init_db()
    
    # Initialize services
    from services.file_service import FileService
    from services.socketio_service import SocketIOService
    from services.notification_service import NotificationService
    from database.connection import get_db
    
    file_service = FileService(config.UPLOAD_FOLDER)
    socketio_service = SocketIOService(socketio, get_db)
    notification_service = NotificationService()
    
    # Store services in app config
    app.config['file_service'] = file_service
    app.config['socketio_service'] = socketio_service
    app.config['notification_service'] = notification_service
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.complaints import complaints_bp
    from routes.admin import admin_bp
    from routes.user import user_bp
    from routes.head import head_bp
    from routes.feedback import feedback_bp
    from routes.messaging import messaging_bp
    from routes.districts import districts_bp
    from routes.dashboard import dashboard_bp
    from routes.admin_head_messaging import admin_head_bp
    from routes.messages import messages_bp
    
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
    
    # Frontend routes
    @app.route('/')
    def index():
        """Serve splash page as index"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), 'splash.html')
    
    @app.route('/splash')
    @app.route('/splash.html')
    def splash():
        """Serve splash page"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), 'splash.html')
    
    @app.route('/login')
    @app.route('/login.html')
    def login():
        """Serve login page"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), 'login.html')
    
    @app.route('/register')
    @app.route('/register.html')
    def register():
        """Serve register page"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), 'register.html')
    
    @app.route('/admin_dashboard')
    @app.route('/admin_dashboard.html')
    def admin_dashboard():
        """Serve admin dashboard"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), 'admin_dashboard.html')
    
    @app.route('/head_dashboard')
    @app.route('/head_dashboard.html')
    def head_dashboard():
        """Serve head dashboard"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), 'head_dashboard.html')
    
    @app.route('/user_dashboard')
    @app.route('/user_dashboard.html')
    def user_dashboard():
        """Serve user dashboard"""
        return send_from_directory(os.path.join(app.static_folder, 'html'), 'user_dashboard.html')
    
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
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """API health check endpoint"""
        return {'status': 'healthy', 'service': 'SERVONIX API'}, 200
    
    # Security headers and CORS middleware
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        # CORS is handled by Flask-CORS extension
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'  # Changed from DENY to allow iframes if needed
        response.headers['X-XSS-Protection'] = '1; mode=block'
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
