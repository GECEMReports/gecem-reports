from app.models.base import Base, TenantModel, TenantScopedModel
from app.models.user import User
from app.models.equipment import Equipment
from app.models.client import Client
from app.models.report import Report
from app.models.falla import (
    Falla,
    FallaFoto,
    Refaccion,
    Cotizacion,
    ProcedimientoReparacion,
    PasoReparacion,
    PasoFoto,
    ReporteCliente,
)

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
