from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class CompanySize(PyEnum):
    STARTUP = "1-50"
    SMALL = "51-200"
    MEDIUM = "201-1000"
    LARGE = "1001-5000"
    ENTERPRISE = "5000+"


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    career_page_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    engineering_blog_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ats_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ats_config: Mapped[dict] = mapped_column(JSON, default=dict)
    ats_changes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    known_tech_stack: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    public_tech_stack: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)

    country_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("countries.id"), nullable=True, index=True
    )
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    visa_sponsorship: Mapped[str] = mapped_column(
        String(16), default="Unknown", nullable=False
    )  # Yes / No / Unknown / Likely
    relocation_assistance: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_policy: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    remote_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    hiring_status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )  # active / paused / closed / unknown
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    glassdoor_rating: Mapped[Optional[float]] = mapped_column(nullable=True)

    first_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_crawled: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    country: Mapped["Country"] = relationship("Country", back_populates="companies")
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="company", lazy="selectin", cascade="all, delete-orphan"
    )
    recruiters: Mapped[list["Recruiter"]] = relationship(
        "Recruiter", back_populates="company", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Company {self.name}>"
