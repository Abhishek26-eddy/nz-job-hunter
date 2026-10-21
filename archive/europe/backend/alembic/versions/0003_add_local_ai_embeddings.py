"""Add local AI embedding columns.

Revision ID: 0003
Revises: 0002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Jobs
    op.add_column("jobs", sa.Column("embedding", sa.JSON(), nullable=True))
    op.add_column(
        "jobs", sa.Column("embedding_model", sa.String(128), nullable=True)
    )
    op.add_column(
        "jobs", sa.Column("ai_reasoned_at", sa.DateTime(timezone=True), nullable=True)
    )

    # Resumes
    op.add_column("resumes", sa.Column("embedding", sa.JSON(), nullable=True))
    op.add_column(
        "resumes", sa.Column("embedding_model", sa.String(128), nullable=True)
    )
    op.add_column(
        "resumes", sa.Column("embedding_content_hash", sa.String(64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("jobs", "embedding")
    op.drop_column("jobs", "embedding_model")
    op.drop_column("jobs", "ai_reasoned_at")
    op.drop_column("resumes", "embedding")
    op.drop_column("resumes", "embedding_model")
    op.drop_column("resumes", "embedding_content_hash")
