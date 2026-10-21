from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Note(Base, TimestampMixin):
    __tablename__ = "notes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    application_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("applications.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return f"<Note {self.id}>"
