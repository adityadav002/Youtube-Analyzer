import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', '')
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_db = os.environ.get('MYSQL_DATABASE', 'youtube_analyzer')
    
    mysql_password = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
    )
    
    # Connection Configuration (from Blueprint)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 5,
        "connect_args": {
            "charset": "utf8mb4",
            "connect_timeout": 10
        }
    }
    
    USE_CELERY = os.environ.get('USE_CELERY', 'true').lower() == 'true'
    
    if USE_CELERY:
        REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        broker_url = REDIS_URL
        result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    else:
        REDIS_URL = None
    
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
    
    DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', os.path.join(os.getcwd(), 'downloads'))
    THUMBNAIL_DIR = os.environ.get('THUMBNAIL_DIR', os.path.join(os.getcwd(), 'thumbnails'))

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    task_always_eager = True
    
    # SQLite-compatible configuration
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {
            "check_same_thread": False
        }
    }

config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig,
    testing=TestingConfig
)
