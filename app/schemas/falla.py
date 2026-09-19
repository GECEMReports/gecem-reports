import uuid
from datetime import datetime

from pydantic import BaseModel


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


class RefaccionCreate(BaseModel):
    nombre: str
    numero_parte: str | None = None
    cantidad: float = 1
    precio_unitario: float | None = None
    moneda: str = "MXN"
    proveedor: str | None = None
    precio_confirmado: bool = False


class RefaccionResponse(BaseModel):
    id: uuid.UUID
    falla_id: uuid.UUID
    nombre: str
    numero_parte: str | None
    cantidad: float
    precio_unitario: float | None
    moneda: str
    proveedor: str | None
    precio_confirmado: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
