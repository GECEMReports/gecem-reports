from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantScopedModel


class Equipment(TenantScopedModel):
    __tablename__ = "equipment"

    brand: Mapped[str] = mapped_column(String(100), nullable=False)  # CAT, Komatsu, John Deere
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(50), nullable=False)  # excavator, loader, bulldozer
    hours: Mapped[float] = mapped_column(Float, default=0)
    year: Mapped[int] = mapped_column(nullable=True)
    client_id: Mapped[str] = mapped_column(String(36), nullable=True)  # FK to clients
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
