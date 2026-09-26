from pydantic import BaseModel


class DiagnosisRequest(BaseModel):
    equipment_id: str
    symptoms: str | None = None
    thread_id: str | None = None
    respuesta_seguimiento: str | None = None


class DiagnosisResponse(BaseModel):
    interrupted: bool = False
    thread_id: str | None = None
    pregunta: str | None = None
    necesita_mas_info: bool | None = None
    pregunta_seguimiento: str | None = None
    problem_type: str | None = None
    diagnosis: str | None = None
    recommendations: list[str] | None = None
    parts_needed: list[str] | None = None
    estimated_hours: float | None = None
    severity: str | None = None
