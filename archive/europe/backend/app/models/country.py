from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Country(Base, TimestampMixin):
    __tablename__ = "countries"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(4), nullable=False, unique=True, index=True)
    region: Mapped[str] = mapped_column(String(64), nullable=True)
    is_eu: Mapped[bool] = mapped_column(default=False)
    visa_notes: Mapped[str] = mapped_column(String(1024), nullable=True)

    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="country", lazy="selectin"
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="country", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Country {self.name}>"
