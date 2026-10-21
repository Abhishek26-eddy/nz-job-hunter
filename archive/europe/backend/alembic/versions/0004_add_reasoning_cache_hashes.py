"""Add reasoning cache hash columns.

Revision ID: 0004
Revises: 0003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("ai_reasoned_description_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("ai_reasoned_resume_hash", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "ai_reasoned_description_hash")
    op.drop_column("jobs", "ai_reasoned_resume_hash")
