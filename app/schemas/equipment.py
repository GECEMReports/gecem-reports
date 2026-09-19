import uuid
from datetime import datetime

from pydantic import BaseModel


class EquipmentCreate(BaseModel):
    brand: str
    model: str
    serial_number: str
    equipment_type: str
    hours: float = 0
    year: int | None = None
    client_id: uuid.UUID | None = None
    notes: str | None = None


class EquipmentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand: str
    model: str
    serial_number: str
    equipment_type: str
    hours: float
    year: int | None
    client_id: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
