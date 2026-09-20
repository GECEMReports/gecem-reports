import uuid
from datetime import datetime

from pydantic import BaseModel


# --- Paso Reparacion ---
class PasoCreate(BaseModel):
    descripcion: str
    tiempo_minutos: float = 0


class PasoResponse(BaseModel):
    id: uuid.UUID
    procedimiento_id: uuid.UUID
    numero_paso: int
    descripcion: str
    tiempo_minutos: float
    fotos: list["PasoFotoResponse"] = []

    model_config = {"from_attributes": True}


class PasoFotoResponse(BaseModel):
    id: uuid.UUID
    filename: str
    filepath: str

    model_config = {"from_attributes": True}


# --- Procedimiento Reparacion ---
class ProcedimientoCreate(BaseModel):
    falla_id: str
    cotizacion_id: str | None = None
    notas: str | None = None


class ProcedimientoResponse(BaseModel):
    id: uuid.UUID
    falla_id: uuid.UUID
    cotizacion_id: uuid.UUID | None
    mecanico_id: uuid.UUID | None
    tiempo_total_horas: float
    notas: str | None
    status: str
    created_at: datetime
    pasos: list[PasoResponse] = []

    model_config = {"from_attributes": True}


class CompletarProcedimientoRequest(BaseModel):
    tiempo_total_horas: float
    notas: str | None = None


# --- Reporte Cliente ---
class ReporteClienteResponse(BaseModel):
    id: uuid.UUID
    falla_id: uuid.UUID
    contenido: str
    pdf_url: str | None
    fecha_generacion: datetime

    model_config = {"from_attributes": True}
