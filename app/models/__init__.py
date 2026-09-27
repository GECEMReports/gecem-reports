from app.models.base import Base, TenantModel, TenantScopedModel
from app.models.user import User
from app.modules.equipment.models import Equipment
from app.models.client import Client
from app.modules.diagnosis.models import Report
from app.models.falla import (
    Cotizacion,
    ProcedimientoReparacion,
    PasoReparacion,
    PasoFoto,
    ReporteCliente,
)
from app.modules.failures.models import Falla, FallaFoto
from app.modules.parts.models import Refaccion

__all__ = [
    "Base",
    "TenantModel",
    "TenantScopedModel",
    "User",
    "Equipment",
    "Client",
    "Report",
    "Falla",
    "FallaFoto",
    "Refaccion",
    "Cotizacion",
    "ProcedimientoReparacion",
    "PasoReparacion",
    "PasoFoto",
    "ReporteCliente",
]
