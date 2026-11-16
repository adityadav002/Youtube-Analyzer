import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath('backend'))

from sqlalchemy.dialects import postgresql, mysql
from sqlalchemy import text

class TestDatabaseCompatibility(unittest.TestCase):
    def test_mysql_specific_sql_in_init(self):
        """
        CRITICAL: Test MySQL-specific SQL statements executed at startup in app/__init__.py.
        PostgreSQL does not support LONGTEXT (it uses TEXT) and does not support
        'ADD FULLTEXT INDEX' syntax.
        """
        init_file = os.path.abspath('backend/app/__init__.py')
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()

        has_longtext = "LONGTEXT" in content
        has_fulltext = "ADD FULLTEXT INDEX" in content

        print("\n--- [AUDIT FINDING] MySQL-Specific DDL in app/__init__.py ---")
        print(f"Contains 'LONGTEXT': {has_longtext}")
        print(f"Contains 'ADD FULLTEXT INDEX': {has_fulltext}")
        print("------------------------------------------------------------\n")

        self.assertTrue(has_longtext, "Expected app/__init__.py to contain hardcoded LONGTEXT DDL")
        self.assertTrue(has_fulltext, "Expected app/__init__.py to contain hardcoded ADD FULLTEXT INDEX DDL")

    def test_render_yaml_specifies_postgresql_while_app_uses_mysql_syntax(self):
        """
        CRITICAL: Verify render.yaml database specification vs backend code.
        """
        render_yaml_path = os.path.abspath('render.yaml')
        with open(render_yaml_path, 'r', encoding='utf-8') as f:
            render_yaml = f.read()

        # Using string matching (pyyaml not in requirements)
        has_pg_db = "youtube-analyzer-db" in render_yaml
        has_free_plan = "plan: free" in render_yaml

        print(f"[AUDIT FINDING] render.yaml specifies Render PostgreSQL DB: {has_pg_db}")
        print(f"[AUDIT FINDING] render.yaml uses free plan for database: {has_free_plan}")

        self.assertTrue(has_pg_db)
        self.assertTrue(has_free_plan)

    def test_build_sh_missing_migrations(self):
        """
        CRITICAL: Verify whether build.sh executes database migrations.
        """
        build_sh_path = os.path.abspath('backend/build.sh')
        with open(build_sh_path, 'r', encoding='utf-8') as f:
            build_sh = f.read()

        has_db_upgrade = "flask db upgrade" in build_sh or "alembic upgrade" in build_sh
        print(f"[AUDIT FINDING] backend/build.sh contains 'flask db upgrade': {has_db_upgrade}")
        self.assertFalse(has_db_upgrade, "backend/build.sh is missing 'flask db upgrade'")

    def test_procfile_missing_migrations(self):
        """
        Verify whether Procfile executes migrations before starting gunicorn.
        """
        procfile_path = os.path.abspath('backend/Procfile')
        with open(procfile_path, 'r', encoding='utf-8') as f:
            procfile = f.read()

        has_db_upgrade = "flask db upgrade" in procfile
        print(f"[AUDIT FINDING] backend/Procfile contains 'flask db upgrade': {has_db_upgrade}")
        self.assertFalse(has_db_upgrade, "Procfile does not run migrations")

if __name__ == '__main__':
    unittest.main()
