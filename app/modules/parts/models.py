import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantScopedModel


class Refaccion(TenantScopedModel):
    __tablename__ = "refacciones"

    falla_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fallas.id"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    numero_parte: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cantidad: Mapped[float] = mapped_column(Float, default=1)
    precio_unitario: Mapped[float | None] = mapped_column(Float, nullable=True)
    moneda: Mapped[str] = mapped_column(String(5), default="MXN")
    proveedor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    precio_confirmado: Mapped[bool] = mapped_column(default=False)  # True = del CSV, False = estimado por LLM
    editado_por_mecanico: Mapped[bool] = mapped_column(default=False)  # True = mecánico cambió el precio antes de confirmar
    status: Mapped[str] = mapped_column(String(20), default="sugerida")  # sugerida, aprobada, comprada, utilizada
