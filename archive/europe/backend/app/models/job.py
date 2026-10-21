from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    platform_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    workplace_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # remote / hybrid / onsite
    employment_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # full-time / contract
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    salary_period: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    country_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("countries.id"), nullable=True, index=True
    )

    # AI / visa fields
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    match_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strengths: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    missing_skills: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    visa_sponsorship_inferred: Mapped[str] = mapped_column(
        String(32), default="Unknown", nullable=False
    )
    salary_estimate: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    should_apply: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tech_stack: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)

    # Local embedding pipeline
    embedding: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ai_reasoned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_reasoned_description_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    ai_reasoned_resume_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )

    # Recruiter-intelligence layer (rule-based, computed on every scoring pass)
    role_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    role_priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    critical_missing_skills: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)

    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    company: Mapped["Company"] = relationship("Company", back_populates="jobs")
    country: Mapped[Optional["Country"]] = relationship("Country", back_populates="jobs")
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="job", lazy="selectin"
    )
    snapshots: Mapped[list["JobSnapshot"]] = relationship(
        "JobSnapshot", back_populates="job", lazy="selectin"
    )

    __table_args__ = (
        # A platform + external_id pair should be unique for active jobs
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<Job {self.title} @ {self.company.name if self.company else '?'}>"
