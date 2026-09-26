"""Diagnosis domain service (thin).

Encapsulates the `diagnose_equipment` business operation, moved verbatim
from the former `app/api/ai/diagnosis.py` endpoint. No logic changes.

Equipment is consumed exclusively through the Equipment module's public
service (`get_equipment_or_404`).
"""

from uuid import uuid4

from fastapi import HTTPException
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.diagnosis.models import Report
from app.modules.diagnosis.schemas import DiagnosisRequest, DiagnosisResponse
from app.modules.equipment.service import get_equipment_or_404
from app.tenancy.middleware import current_tenant_id


async def diagnose_equipment(req: DiagnosisRequest, db: AsyncSession) -> DiagnosisResponse:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify equipment belongs to tenant
    equipment = await get_equipment_or_404(db, req.equipment_id)

    from app.modules.diagnosis.agent import diagnosis_agent

    if diagnosis_agent is None:
        raise HTTPException(503, "Diagnosis agent is not initialized")

    thread_id = req.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    if req.respuesta_seguimiento is not None:
        graph_input = Command(resume=req.respuesta_seguimiento)
    else:
        if not req.symptoms or not req.symptoms.strip():
            raise HTTPException(422, "symptoms is required for a new diagnosis")
        graph_input = {
            "messages": [],
            "equipment_id": req.equipment_id,
            "symptoms": req.symptoms,
            "equipment_info": {},
            "diagnosis": "",
            "recommendations": [],
            "parts_needed": [],
            "estimated_hours": 0.0,
            "severity": "medium",
            "problem_type": "",
            "necesita_mas_info": False,
            "pregunta_seguimiento": "",
            "detail_rounds": 0,
        }

    final_state = await diagnosis_agent.ainvoke(graph_input, config=config)

    interrupts = final_state.get("__interrupt__", ())
    if interrupts:
        value = getattr(interrupts[0], "value", interrupts[0])
        question = value.get("pregunta", str(value)) if isinstance(value, dict) else str(value)
        return DiagnosisResponse(
            interrupted=True,
            thread_id=thread_id,
            pregunta=question,
        )

    # If the agent needs more info, return just that
    if final_state.get("necesita_mas_info"):
        return DiagnosisResponse(
            thread_id=thread_id,
            necesita_mas_info=True,
            pregunta_seguimiento=final_state.get("pregunta_seguimiento", ""),
        )

    # Save report only if we have a complete diagnosis
    report = Report(
        tenant_id=tenant_id,
        equipment_id=req.equipment_id,
        client_id=equipment.client_id,
        title=f"Diagnostico: {equipment.brand} {equipment.model}",
        report_type="diagnosis",
        symptoms=final_state.get("symptoms", req.symptoms or ""),
        diagnosis=final_state.get("diagnosis", ""),
        recommendations="\n".join(final_state.get("recommendations", [])),
        parts_needed="\n".join(final_state.get("parts_needed", [])),
        estimated_hours=final_state.get("estimated_hours", 0.0),
        status="completed",
    )
    db.add(report)
    await db.commit()

    return DiagnosisResponse(
        thread_id=thread_id,
        necesita_mas_info=False,
        problem_type=final_state.get("problem_type", ""),
        diagnosis=final_state.get("diagnosis", ""),
        recommendations=final_state.get("recommendations", []),
        parts_needed=final_state.get("parts_needed", []),
        estimated_hours=final_state.get("estimated_hours", 0.0),
        severity=final_state.get("severity", "medium"),
    )
