import os
import logging
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import config_by_name

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
limiter = Limiter(key_func=get_remote_address, storage_uri='memory://')

def validate_startup_config(app, config_name):
    if config_name == 'production':
        secret = os.environ.get('SECRET_KEY') or app.config.get('SECRET_KEY')
        if not secret or secret == 'dev-key-change-me':
            raise ValueError("CRITICAL CONFIGURATION ERROR: SECRET_KEY must be set to a secure random value in production.")
        
        db_url = os.environ.get('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI')
        if not db_url:
            raise ValueError("CRITICAL CONFIGURATION ERROR: DATABASE_URL is missing in production environment.")
            
        yt_key = os.environ.get('YOUTUBE_API_KEY')
        if not yt_key:
            raise ValueError("CRITICAL CONFIGURATION ERROR: YOUTUBE_API_KEY must be set in production environment.")
    else:
        secret = os.environ.get('SECRET_KEY') or app.config.get('SECRET_KEY')
        if not secret or secret == 'dev-key-change-me':
            logging.warning("WARNING: Running with default dev SECRET_KEY.")
        if not os.environ.get('YOUTUBE_API_KEY'):
            logging.warning("WARNING: YOUTUBE_API_KEY is not set. YouTube Data API calls will fail.")

def cleanup_orphaned_jobs(app):
    """
    On startup, marks any jobs left in 'processing' or 'queued' state from a previous
    process/container restart as 'failed'.
    """
    try:
        with app.app_context():
            from app.models.queue import ProcessingQueue
            orphaned = db.session.query(ProcessingQueue).filter(
                ProcessingQueue.status.in_(['processing', 'queued'])
            ).all()
            if orphaned:
                for job in orphaned:
                    job.status = 'failed'
                    job.error_message = 'Job terminated prematurely due to server restart.'
                db.session.commit()
                logging.getLogger(__name__).info(f"Cleaned up {len(orphaned)} orphaned background jobs.")
    except Exception as e:
        # Table might not exist yet before first migration
        logging.getLogger(__name__).debug(f"Could not clean up orphaned jobs: {e}")

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
        
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    if 'SECRET_KEY' in os.environ:
        app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    if 'DATABASE_URL' in os.environ:
        db_url = os.environ['DATABASE_URL']
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url

    # Validate configuration on startup
    validate_startup_config(app, config_name)

    # Configure logging
    logging.basicConfig(level=app.config.get('LOG_LEVEL', 'INFO'))

    # Initialize extensions
    db.init_app(app)
    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
    migrate.init_app(app, db, directory=migrations_dir)
    cors.init_app(app, origins=app.config['CORS_ORIGINS'])
    limiter.init_app(app)


    # Import and register models so Alembic can find them
    from app import models
    
    # Register middleware
    from app.middleware.error_handlers import register_error_handlers
    from app.middleware.request_logger import register_request_logger
    register_error_handlers(app)
    # Register blueprints (to be added in later milestones)
    from app.controllers.channel_controller import channel_bp
    from app.controllers.video_controller import video_bp
    from app.controllers.jobs_controller import jobs_bp
    from app.controllers.download_controller import download_bp
    from app.controllers.dashboard_controller import dashboard_bp
    from app.controllers.search_controller import search_bp
    from app.controllers.settings_controller import settings_bp
    from app.controllers.ai_controller import ai_bp
    
    app.register_blueprint(channel_bp)
    app.register_blueprint(video_bp, url_prefix='/api/videos')
    app.register_blueprint(jobs_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(settings_bp)
    app.register_blueprint(ai_bp)

    register_request_logger(app)
    
    # Serve thumbnails statically in production/local dev without Nginx
    @app.route('/thumbnails/<path:filename>')
    def serve_thumbnail(filename):
        from flask import send_from_directory
        return send_from_directory(app.config['THUMBNAIL_DIR'], filename)

    # Register basic health endpoint
    @app.route('/api/health')
    def health_check():
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as e:
            logging.error(f"Health check DB probe failed: {e}")
            return jsonify({"status": "error", "db": "unreachable"}), 503
            
        resp_data = {"status": "ok", "db": "ok"}
        if app.config.get('USE_CELERY'):
            resp_data["redis"] = "ok"
        return jsonify(resp_data), 200

    cleanup_orphaned_jobs(app)

    return app
