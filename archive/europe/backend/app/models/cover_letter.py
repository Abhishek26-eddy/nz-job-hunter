from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class CoverLetter(Base, TimestampMixin):
    __tablename__ = "cover_letters"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    word_count: Mapped[int] = mapped_column(default=0)

    user: Mapped["User"] = relationship("User", back_populates="cover_letters")
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="cover_letter", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<CoverLetter {self.title}>"
