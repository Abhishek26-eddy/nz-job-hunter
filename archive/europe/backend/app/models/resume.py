from typing import Optional

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin




class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tailored_for_job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id"), nullable=True
    )

    # Local embedding pipeline
    embedding: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Structured profile extracted from resume text (cached, rebuilt on content change)
    profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    profile_content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="resumes")
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="resume", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Resume {self.name}>"
