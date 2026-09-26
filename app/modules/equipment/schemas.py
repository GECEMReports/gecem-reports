import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EquipmentCreate(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    serial_number: str = Field(..., min_length=1, max_length=100)
    equipment_type: str = Field(..., min_length=1, max_length=50)
    hours: float = Field(default=0, ge=0)
    year: int | None = Field(default=None, ge=1900, le=2100)
    client_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class EquipmentUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    brand: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    serial_number: str | None = Field(default=None, min_length=1, max_length=100)
    equipment_type: str | None = Field(default=None, min_length=1, max_length=50)
    hours: float | None = Field(default=None, ge=0)
    year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = Field(default=None, max_length=1000)


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
