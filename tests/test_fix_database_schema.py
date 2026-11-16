import sys
import os
import unittest
import re

sys.path.insert(0, os.path.abspath('backend'))

class TestDatabaseSchemaFixes(unittest.TestCase):
    def test_app_init_has_no_raw_ddl_swallowing(self):
        """
        Fix 1 / YA-002: Ensure app/__init__.py does NOT contain raw DDL execution
        or silent swallowing of database schema alter statements.
        """
        init_file = os.path.abspath('backend/app/__init__.py')
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should not have LONGTEXT or ADD FULLTEXT INDEX
        self.assertNotIn("LONGTEXT", content, "app/__init__.py must not contain MySQL LONGTEXT raw DDL")
        self.assertNotIn("ADD FULLTEXT INDEX", content, "app/__init__.py must not contain raw FULLTEXT DDL")
        self.assertNotIn("ALTER TABLE search_history", content, "app/__init__.py must not execute raw ALTER TABLE")
        self.assertNotIn("ALTER TABLE transcripts", content, "app/__init__.py must not execute raw ALTER TABLE")

    def test_migration_cc6d68dead72_has_no_mysql_dialect_import(self):
        """
        Fix 1 / YA-003: Migration cc6d68dead72 must use generic SQLAlchemy types,
        not sqlalchemy.dialects.mysql.VARCHAR.
        """
        mig_file = os.path.abspath('backend/migrations/versions/cc6d68dead72_increase_target_id_length.py')
        with open(mig_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertNotIn("sqlalchemy.dialects.mysql", content, "Migration must not import mysql dialect directly")
        self.assertNotIn("mysql.VARCHAR", content, "Migration must use generic sa.String instead of mysql.VARCHAR")

    def test_latest_migration_adds_results_json_idempotently(self):
        """
        Fix 1 / YA-002: A migration must exist adding results_json as sa.Text() to search_history,
        checking column existence to be safe on existing MySQL databases.
        """
        versions_dir = os.path.abspath('backend/migrations/versions')
        files = [f for f in os.listdir(versions_dir) if f.endswith('.py') and not f.startswith('__')]
        
        found_results_json_migration = False
        for f in files:
            with open(os.path.join(versions_dir, f), 'r', encoding='utf-8') as fp:
                txt = fp.read()
                if "results_json" in txt:
                    found_results_json_migration = True
                    self.assertIn("sa.Text", txt, "results_json column must use generic sa.Text()")
                    # Must be idempotent: check columns or inspector
                    self.assertTrue(
                        "inspector" in txt or "columns" in txt or "if_not_exists" in txt,
                        "results_json migration must be idempotent"
                    )
                    break
        
        self.assertTrue(found_results_json_migration, "Must have an Alembic migration for search_history.results_json")

    def test_postgres_orm_query_compilation(self):
        """
        Compile core ORM queries with PostgreSQL dialect to verify no MySQL-only constructs exist in queries.
        """
        from sqlalchemy.dialects import postgresql
        from app.models.channel import Channel
        from app.models.video import Video
        from app.models.history import SearchHistory, DownloadHistory
        from app.models.transcript import Transcript
        from app import db, create_app

        app = create_app('testing')
        with app.app_context():
            # Test compiling Video query
            q1 = db.session.query(Video).filter(Video.is_short == True, Video.channel_id == 'test')
            compiled_sql_1 = str(q1.statement.compile(dialect=postgresql.dialect()))
            self.assertIn('videos.is_short = true', compiled_sql_1.lower())

            # Test compiling SearchHistory query with results_json
            q2 = db.session.query(SearchHistory).filter(SearchHistory.query == 'test')
            compiled_sql_2 = str(q2.statement.compile(dialect=postgresql.dialect()))
            self.assertIn('search_history.results_json', compiled_sql_2.lower())

            # Test compiling Transcript query
            q3 = db.session.query(Transcript).filter(Transcript.video_id == 'test')
            compiled_sql_3 = str(q3.statement.compile(dialect=postgresql.dialect()))
            self.assertIn('transcripts.full_text', compiled_sql_3.lower())

if __name__ == '__main__':
    unittest.main()

