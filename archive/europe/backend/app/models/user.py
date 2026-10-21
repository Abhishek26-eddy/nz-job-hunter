from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    preferred_roles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_countries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[Optional[int]] = mapped_column(nullable=True)

    resumes: Mapped[list["Resume"]] = relationship(
        "Resume", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[list["CoverLetter"]] = relationship(
        "CoverLetter", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
