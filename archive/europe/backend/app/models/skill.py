from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=True)
    aliases: Mapped[str] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return f"<Skill {self.name}>"
