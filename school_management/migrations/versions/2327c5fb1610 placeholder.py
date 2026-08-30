"""placeholder for lost initial migration

Revision ID: 2327c5fb1610
Revises: 
Create Date: 2026-08-30 00:00:00.000000

This file was reconstructed to patch a broken Alembic history. The live
database's alembic_version table already recorded '2327c5fb1610' as its
current revision, but the original migration file that created it was
lost (never committed, or dropped during a project restructure).

The actual schema for this revision already exists in the database and
matches the current models exactly (verified via \\d against Postgres),
so upgrade()/downgrade() are intentionally no-ops. This file exists only
so Alembic can locate the revision id and resume building new migrations
on top of it.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2327c5fb1610'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # No-op: schema for this revision already exists in the live database.
    pass


def downgrade():
    # No-op: intentionally left blank. If you ever need to actually tear
    # down the schema, do NOT rely on this file — it does not know how
    # to reverse the original (lost) migration's changes.
    pass