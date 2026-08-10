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
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
        
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Configure logging
    logging.basicConfig(level=app.config.get('LOG_LEVEL', 'INFO'))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, origins=app.config['CORS_ORIGINS'])
    limiter.init_app(app)
    
    # Database schema check and updates on startup
    with app.app_context():
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'search_history' in tables:
                columns = [col['name'] for col in inspector.get_columns('search_history')]
                if 'results_json' not in columns:
                    db.session.execute(text("ALTER TABLE search_history ADD COLUMN results_json LONGTEXT NULL"))
                    db.session.commit()
                    logging.info("Added 'results_json' column to 'search_history' table.")
                    
            if 'transcripts' in tables:
                indexes = inspector.get_indexes('transcripts')
                has_fulltext = any(idx['name'] == 'idx_transcripts_full_text' for idx in indexes)
                if not has_fulltext:
                    db.session.execute(text("ALTER TABLE transcripts ADD FULLTEXT INDEX idx_transcripts_full_text (full_text)"))
                    db.session.commit()
                    logging.info("Added FULLTEXT index 'idx_transcripts_full_text' to 'transcripts' table.")
        except Exception as e:
            logging.error(f"Error checking/updating database schema: {e}")
            db.session.rollback()


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
    
    app.register_blueprint(channel_bp)
    app.register_blueprint(video_bp, url_prefix='/api/videos')
    app.register_blueprint(jobs_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(settings_bp)

    register_request_logger(app)
    
    # Register basic health endpoint
    @app.route('/api/health')
    def health_check():
        redis_status = "ok" if app.config.get('USE_CELERY') else "disabled"
        return jsonify({"status": "ok", "db": "ok", "redis": redis_status})

    return app
