"""add_results_json_and_transcript_index

Revision ID: d4e5f6a7b8c9
Revises: cc6d68dead72
Create Date: 2026-11-16 14:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'cc6d68dead72'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Idempotently add results_json to search_history if table exists
    if 'search_history' in tables:
        columns = [col['name'] for col in inspector.get_columns('search_history')]
        if 'results_json' not in columns:
            with op.batch_alter_table('search_history', schema=None) as batch_op:
                batch_op.add_column(sa.Column('results_json', sa.Text(), nullable=True))

    # 2. Idempotently add transcript fulltext index per dialect
    if 'transcripts' in tables:
        indexes = inspector.get_indexes('transcripts')
        has_idx = any(idx['name'] == 'idx_transcripts_full_text' for idx in indexes)
        if not has_idx:
            if bind.dialect.name == 'mysql':
                op.execute(sa.text("ALTER TABLE transcripts ADD FULLTEXT INDEX idx_transcripts_full_text (full_text)"))
            elif bind.dialect.name == 'postgresql':
                op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_transcripts_full_text ON transcripts USING gin(to_tsvector('english', full_text))"))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'transcripts' in tables:
        indexes = inspector.get_indexes('transcripts')
        has_idx = any(idx['name'] == 'idx_transcripts_full_text' for idx in indexes)
        if has_idx:
            if bind.dialect.name == 'mysql':
                op.execute(sa.text("ALTER TABLE transcripts DROP INDEX idx_transcripts_full_text"))
            elif bind.dialect.name == 'postgresql':
                op.execute(sa.text("DROP INDEX IF EXISTS idx_transcripts_full_text"))

    if 'search_history' in tables:
        columns = [col['name'] for col in inspector.get_columns('search_history')]
        if 'results_json' in columns:
            with op.batch_alter_table('search_history', schema=None) as batch_op:
                batch_op.drop_column('results_json')

