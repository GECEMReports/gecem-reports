import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedModel


class Falla(TenantScopedModel):
    __tablename__ = "fallas"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=False, index=True
    )
    diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id"), nullable=True
    )
    parte: Mapped[str] = mapped_column(String(200), nullable=False)
    pieza: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    causa_raiz: Mapped[str | None] = mapped_column(Text, nullable=True)
    prioridad: Mapped[str] = mapped_column(String(20), default="normal")  # baja, normal, urgente, critica
    status: Mapped[str] = mapped_column(String(30), default="detectada")  # detectada, en_reparacion, terminada
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    fotos = relationship("FallaFoto", back_populates="falla", cascade="all, delete-orphan")


class FallaFoto(TenantScopedModel):
    __tablename__ = "falla_fotos"

    falla_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fallas.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1000), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    falla = relationship("Falla", back_populates="fotos")
