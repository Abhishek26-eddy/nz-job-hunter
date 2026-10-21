from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class JobSnapshot(Base, TimestampMixin):
    __tablename__ = "job_snapshots"

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    description_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[Optional[int]] = mapped_column(nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(nullable=True)
    changed_fields: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    job: Mapped["Job"] = relationship("Job", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<JobSnapshot job_id={self.job_id}>"
