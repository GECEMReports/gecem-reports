import uuid
from datetime import datetime

from pydantic import BaseModel


class FallaAgentRequest(BaseModel):
    equipment_id: str
    diagnostico_ia: str
    descripcion_mecanico: str


class FallaAgentResponse(BaseModel):
    necesita_mas_info: bool
    pregunta_seguimiento: str | None = None
    falla_estructurada: dict | None = None


class FallaFotoResponse(BaseModel):
    id: uuid.UUID
    filename: str
    filepath: str
    descripcion: str | None

    model_config = {"from_attributes": True}


class FallaCreate(BaseModel):
    equipment_id: str
    diagnosis_id: str | None = None
    parte: str
    pieza: str
    descripcion: str
    causa_raiz: str | None = None
    prioridad: str = "normal"
    notas: str | None = None


class FallaResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    equipment_id: uuid.UUID
    diagnosis_id: uuid.UUID | None
    parte: str
    pieza: str
    descripcion: str
    causa_raiz: str | None
    prioridad: str
    status: str
    notas: str | None
    created_at: datetime
    fotos: list[FallaFotoResponse] = []

    model_config = {"from_attributes": True}


class FallaUpdate(BaseModel):
    parte: str | None = None
    pieza: str | None = None
    descripcion: str | None = None
    causa_raiz: str | None = None
    prioridad: str | None = None
    status: str | None = None
    notas: str | None = None
