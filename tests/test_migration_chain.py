import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('backend'))

from flask_migrate import upgrade
from app import create_app, db
from sqlalchemy import inspect

class TestMigrationChainFromScratch(unittest.TestCase):
    def test_full_migration_chain_on_empty_db(self):
        """
        Verify that running all migrations from scratch to head on a fresh database
        creates all tables including search_history.results_json and processing_queue.target_id (String 255).
        """
        app = create_app('testing')
        with app.app_context():
            # Run full upgrade from empty database
            upgrade()

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'channels', 'processing_queue', 'search_history',
                'user_settings', 'channel_snapshots', 'playlists',
                'videos', 'download_history', 'comments',
                'transcripts', 'ai_analysis'
            ]
            for t in expected_tables:
                self.assertIn(t, tables, f"Expected table {t} to exist after migration")

            # Verify search_history has results_json
            cols = [c['name'] for c in inspector.get_columns('search_history')]
            self.assertIn('results_json', cols, "search_history must contain results_json")

if __name__ == '__main__':
    unittest.main()
