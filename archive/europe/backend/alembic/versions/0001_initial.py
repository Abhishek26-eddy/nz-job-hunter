"""Initial migration

Revision ID: 0001
Revises:
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(128), nullable=False, index=True),
        sa.Column("code", sa.String(4), nullable=False, unique=True, index=True),
        sa.Column("region", sa.String(64), nullable=True),
        sa.Column("is_eu", sa.Boolean(), default=False),
        sa.Column("visa_notes", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("aliases", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_superuser", sa.Boolean(), default=False),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("portfolio_url", sa.String(512), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("location", sa.String(128), nullable=True),
        sa.Column("preferred_roles", sa.Text(), nullable=True),
        sa.Column("preferred_countries", sa.Text(), nullable=True),
        sa.Column("years_of_experience", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("slug", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("career_page_url", sa.String(512), nullable=True),
        sa.Column("ats_provider", sa.String(64), nullable=True),
        sa.Column("ats_config", sa.JSON(), default=dict),
        sa.Column("industry", sa.String(128), nullable=True),
        sa.Column("size", sa.String(32), nullable=True),
        sa.Column("known_tech_stack", sa.JSON(), default=list),
        sa.Column("country_id", sa.Integer(), sa.ForeignKey("countries.id"), nullable=True, index=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("visa_sponsorship", sa.String(16), default="Unknown", nullable=False),
        sa.Column("relocation_assistance", sa.Boolean(), default=False),
        sa.Column("remote_policy", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("glassdoor_rating", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "recruiters",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(128), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_hiring_manager", sa.Boolean(), default=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("external_id", sa.String(255), nullable=False, index=True),
        sa.Column("platform", sa.String(64), nullable=False, index=True),
        sa.Column("platform_url", sa.String(1024), nullable=False),
        sa.Column("title", sa.String(512), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_hash", sa.String(64), nullable=False, index=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("workplace_type", sa.String(32), nullable=True),
        sa.Column("employment_type", sa.String(32), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(8), nullable=True),
        sa.Column("salary_period", sa.String(16), nullable=True),
        sa.Column("application_url", sa.String(1024), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, index=True),
        sa.Column("is_deleted", sa.Boolean(), default=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("country_id", sa.Integer(), sa.ForeignKey("countries.id"), nullable=True, index=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("strengths", sa.JSON(), default=list),
        sa.Column("missing_skills", sa.JSON(), default=list),
        sa.Column("visa_sponsorship_inferred", sa.String(32), default="Unknown"),
        sa.Column("salary_estimate", sa.String(128), nullable=True),
        sa.Column("should_apply", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("tech_stack", sa.JSON(), default=list),
        sa.Column("raw_data", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_master", sa.Boolean(), default=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("skills", sa.JSON(), default=list),
        sa.Column("file_url", sa.String(1024), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("tailored_for_job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "cover_letters",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_url", sa.String(1024), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("word_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False, index=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("cover_letter_id", sa.Integer(), sa.ForeignKey("cover_letters.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), default="saved", nullable=False, index=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_time_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "job_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False, index=True),
        sa.Column("description_hash", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("changed_fields", sa.JSON(), default=list),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("min_match_score", sa.Integer(), nullable=True),
        sa.Column("countries", sa.Text(), nullable=True),
        sa.Column("remote_only", sa.Boolean(), default=False),
        sa.Column("visa_sponsorship", sa.Boolean(), default=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("channel", sa.String(32), default="email"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("notes")
    op.drop_table("job_snapshots")
    op.drop_table("applications")
    op.drop_table("cover_letters")
    op.drop_table("resumes")
    op.drop_table("jobs")
    op.drop_table("recruiters")
    op.drop_table("companies")
    op.drop_table("users")
    op.drop_table("skills")
    op.drop_table("countries")
