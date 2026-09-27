from datetime import datetime
import uuid

from pydantic import BaseModel


class CotizacionCreate(BaseModel):
    falla_id: str
    tipo: str = "manual"  # manual, agente
    subtotal_refacciones: float = 0
    mano_de_obra: float = 0
    moneda: str = "MXN"
    notas: str | None = None


class CotizacionResponse(BaseModel):
    id: uuid.UUID
    falla_id: uuid.UUID
    equipment_id: uuid.UUID
    tipo: str
    subtotal_refacciones: float
    mano_de_obra: float
    total: float
    moneda: str
    notas: str | None
    fecha_vencimiento: datetime | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerarCotizacionRequest(BaseModel):
    falla_id: str


class CotizacionAgentResponse(BaseModel):
    interrupted: bool = False
    thread_id: str | None = None
    pregunta: str | None = None
    subtotal_refacciones: float | None = None
    moneda: str | None = None
    cotizacion: CotizacionResponse | None = None
