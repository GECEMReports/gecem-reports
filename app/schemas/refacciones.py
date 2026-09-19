from pydantic import BaseModel


class RefaccionSugerida(BaseModel):
    nombre: str
    numero_parte: str | None = None
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
