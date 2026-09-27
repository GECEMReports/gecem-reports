import uuid
from datetime import datetime

from pydantic import BaseModel


class RefaccionSugerida(BaseModel):
    nombre: str
    numero_parte: str | None = None
    pn_verificado: bool = False
    cantidad: float = 1
    precio_estimado: float | None = None
    moneda: str = "MXN"
    prioridad: str = "normal"
    precio_confirmado: bool = False
    editado_por_mecanico: bool = False


class SugerirRefaccionesRequest(BaseModel):
    falla_id: str


class SugerirRefaccionesResponse(BaseModel):
    refacciones: list[RefaccionSugerida]
    notas: str = ""


class ConfirmarRefaccionItem(BaseModel):
    nombre: str
    numero_parte: str | None = None
    cantidad: float = 1
    precio_unitario: float | None = None
    moneda: str = "MXN"
    prioridad: str = "normal"
    precio_confirmado: bool = True
    editado_por_mecanico: bool = False


class ConfirmarRefaccionesRequest(BaseModel):
    falla_id: str
    refacciones: list[ConfirmarRefaccionItem]


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
    editado_por_mecanico: bool = False
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
