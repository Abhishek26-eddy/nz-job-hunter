from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ApplicationStatus:
    SAVED = "saved"
    APPLIED = "applied"
    OA = "oa"
    RECRUITER_CALL = "recruiter_call"
    INTERVIEW = "interview"
    FINAL_ROUND = "final_round"
    OFFER = "offer"
    REJECTED = "rejected"
    GHOSTED = "ghosted"
    WITHDRAWN = "withdrawn"


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    resume_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("resumes.id"), nullable=True
    )
    cover_letter_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cover_letters.id"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    status: Mapped[str] = mapped_column(
        String(32), default=ApplicationStatus.SAVED, nullable=False, index=True
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    response_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    resume: Mapped[Optional["Resume"]] = relationship("Resume", back_populates="applications")
    cover_letter: Mapped[Optional["CoverLetter"]] = relationship(
        "CoverLetter", back_populates="applications"
    )

    def __repr__(self) -> str:
        return f"<Application {self.id}: {self.status}>"
