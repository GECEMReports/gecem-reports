import uuid
from datetime import datetime

from pydantic import BaseModel


# Placeholder ETAPA Repairs: este schema pertenece a Reports y se
# reubicara con el resto del dominio en su propia etapa.
class ReporteClienteResponse(BaseModel):
    id: uuid.UUID
    falla_id: uuid.UUID
    contenido: str
    pdf_url: str | None
    fecha_generacion: datetime

    model_config = {"from_attributes": True}
