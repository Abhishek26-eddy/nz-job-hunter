from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    min_match_score: Mapped[Optional[int]] = mapped_column(nullable=True)
    countries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remote_only: Mapped[bool] = mapped_column(Boolean, default=False)
    visa_sponsorship: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    channel: Mapped[str] = mapped_column(String(32), default="email")  # email/slack/etc

    def __repr__(self) -> str:
        return f"<Alert {self.name}>"
