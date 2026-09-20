import uuid
from datetime import datetime, timedelta

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
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


class ReporteCliente(TenantScopedModel):
    __tablename__ = "reportes_cliente"

    falla_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fallas.id"), nullable=False, index=True
    )
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    fecha_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
