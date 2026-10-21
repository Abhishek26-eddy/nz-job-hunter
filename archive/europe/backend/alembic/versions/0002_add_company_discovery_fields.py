"""Add company discovery and quality fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("engineering_blog_url", sa.String(512), nullable=True))
    op.add_column("companies", sa.Column("public_tech_stack", sa.JSON(), nullable=True))
    op.add_column("companies", sa.Column("remote_friendly", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("companies", sa.Column("hiring_status", sa.String(32), server_default="active", nullable=False))
    op.add_column("companies", sa.Column("ats_changes", sa.Integer(), server_default="0", nullable=False))
    op.add_column("companies", sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("last_crawled", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("jobs_found", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("companies", "engineering_blog_url")
    op.drop_column("companies", "public_tech_stack")
    op.drop_column("companies", "remote_friendly")
    op.drop_column("companies", "hiring_status")
    op.drop_column("companies", "ats_changes")
    op.drop_column("companies", "first_seen")
    op.drop_column("companies", "last_seen")
    op.drop_column("companies", "last_crawled")
    op.drop_column("companies", "jobs_found")
