"""Add recruiter-intelligence fields for role classification, mandatory
filtering, and structured resume profile.

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("role_category", sa.String(64), nullable=True))
    op.add_column("jobs", sa.Column("role_priority", sa.String(16), nullable=True))
    op.add_column("jobs", sa.Column("rejected", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("jobs", sa.Column("rejection_reason", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("score_breakdown", sa.JSON(), nullable=True))
    op.add_column("jobs", sa.Column("critical_missing_skills", sa.JSON(), nullable=True))

    op.add_column("resumes", sa.Column("profile", sa.JSON(), nullable=True))
    op.add_column("resumes", sa.Column("profile_content_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "profile_content_hash")
    op.drop_column("resumes", "profile")

    op.drop_column("jobs", "critical_missing_skills")
    op.drop_column("jobs", "score_breakdown")
    op.drop_column("jobs", "rejection_reason")
    op.drop_column("jobs", "rejected")
    op.drop_column("jobs", "role_priority")
    op.drop_column("jobs", "role_category")
