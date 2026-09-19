from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantScopedModel


class Client(TenantScopedModel):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
