import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath('backend'))

class TestStartupValidationAndHealth(unittest.TestCase):
    def test_production_fails_without_youtube_api_key(self):
        """
        Fix 3: In production, app must fail fast if YOUTUBE_API_KEY is missing.
        """
        from app import create_app
        env = {
            'FLASK_ENV': 'production',
            'SECRET_KEY': 'valid-prod-secret-key-12345',
            'DATABASE_URL': 'sqlite:///:memory:',
            'YOUTUBE_API_KEY': ''
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError) as ctx:
                create_app('production')
            self.assertIn("YOUTUBE_API_KEY", str(ctx.exception))

    def test_production_fails_with_default_secret_key(self):
        """
        Fix 3: In production, app must fail fast if SECRET_KEY is 'dev-key-change-me'.
        """
        from app import create_app
        env = {
            'FLASK_ENV': 'production',
            'SECRET_KEY': 'dev-key-change-me',
            'DATABASE_URL': 'sqlite:///:memory:',
            'YOUTUBE_API_KEY': 'test_key'
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError) as ctx:
                create_app('production')
            self.assertIn("SECRET_KEY", str(ctx.exception))

    def test_development_warns_without_crashing(self):
        """
        Fix 3: In development, app should boot with warnings even if keys are default.
        """
        from app import create_app
        env = {
            'FLASK_ENV': 'development',
            'SECRET_KEY': 'dev-key-change-me',
            'YOUTUBE_API_KEY': ''
        }
        with patch.dict(os.environ, env, clear=True):
            # Development should not raise
            app = create_app('development')
            self.assertIsNotNone(app)

    def test_use_celery_defaults_to_false(self):
        """
        Fix 3: USE_CELERY must default to False so missing env var does not expect Redis.
        """
        from app.config import Config
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(Config.USE_CELERY)

    def test_health_check_returns_503_on_db_failure(self):
        """
        Fix 3: /api/health must return 503 if database check fails.
        """
        from app import create_app, db
        app = create_app('testing')
        client = app.test_client()

        with app.app_context():
            # Mock db.session.execute to simulate database failure
            with patch.object(db.session, 'execute', side_effect=Exception("DB connection refused")):
                res = client.get('/api/health')
                self.assertEqual(res.status_code, 503)
                data = res.get_json()
                self.assertEqual(data.get('status'), 'error')
                self.assertEqual(data.get('db'), 'unreachable')

if __name__ == '__main__':
    unittest.main()

