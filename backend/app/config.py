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

    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
        )
    
    # Connection Configuration (from Blueprint)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 5
    }
    
    if SQLALCHEMY_DATABASE_URI.startswith("mysql"):
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {
            "charset": "utf8mb4",
            "connect_timeout": 10
        }
    
    USE_CELERY = os.environ.get('USE_CELERY', 'false').lower() == 'true'
    
    if USE_CELERY:
        REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        broker_url = REDIS_URL
        result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    else:
        REDIS_URL = None
    
    CORS_ORIGINS = [orig.strip() for orig in os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',') if orig.strip()]
    
    DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', os.path.join(os.getcwd(), 'downloads'))
    THUMBNAIL_DIR = os.environ.get('THUMBNAIL_DIR', os.path.join(os.getcwd(), 'thumbnails'))
    
    is_render = os.environ.get('RENDER') == 'true'
    ENABLE_DOWNLOADS = os.environ.get('ENABLE_DOWNLOADS', 'false' if is_render else 'true').lower() == 'true'
    ENABLE_LOCAL_FILE_OPEN = os.environ.get('ENABLE_LOCAL_FILE_OPEN', 'false' if is_render else 'true').lower() == 'true'
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    SEARCH_CACHE_TTL_HOURS = int(os.environ.get('SEARCH_CACHE_TTL_HOURS', '24'))
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'gemini')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('AI_API_KEY')
    AI_MODEL = os.environ.get('AI_MODEL', 'gemini-2.5-flash')

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
