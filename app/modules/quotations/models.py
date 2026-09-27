import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantScopedModel


class Cotizacion(TenantScopedModel):
    __tablename__ = "cotizaciones"

    falla_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fallas.id"), nullable=False, index=True
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), default="manual")  # manual, agente
    subtotal_refacciones: Mapped[float] = mapped_column(Float, default=0)
    mano_de_obra: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    moneda: Mapped[str] = mapped_column(String(5), default="MXN")
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_vencimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="borrador")  # borrador, enviada, aprobada, rechazada
