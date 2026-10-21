from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Recruiter(Base, TimestampMixin):
    __tablename__ = "recruiters"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_hiring_manager: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="recruiters")

    def __repr__(self) -> str:
        return f"<Recruiter {self.name}>"
