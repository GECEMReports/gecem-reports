import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedModel


class ProcedimientoReparacion(TenantScopedModel):
    __tablename__ = "procedimientos_reparacion"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=False, index=True
    )
    falla_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fallas.id"), nullable=True, index=True
    )
    cotizacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cotizaciones.id"), nullable=True
    )
    mecanico_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tipo: Mapped[str] = mapped_column(String(30), default="correctiva")  # preventiva, correctiva, emergencia
    tiempo_total_horas: Mapped[float] = mapped_column(Float, default=0)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="en_progreso")  # en_progreso, completado

    pasos = relationship("PasoReparacion", back_populates="procedimiento", cascade="all, delete-orphan")


class PasoReparacion(TenantScopedModel):
    __tablename__ = "pasos_reparacion"

    procedimiento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procedimientos_reparacion.id"), nullable=False, index=True
    )
    numero_paso: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    tiempo_minutos: Mapped[float] = mapped_column(Float, default=0)

    procedimiento = relationship("ProcedimientoReparacion", back_populates="pasos")
    fotos = relationship("PasoFoto", back_populates="paso", cascade="all, delete-orphan")


class PasoFoto(TenantScopedModel):
    __tablename__ = "paso_fotos"

    paso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pasos_reparacion.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1000), nullable=False)

    paso = relationship("PasoReparacion", back_populates="fotos")
