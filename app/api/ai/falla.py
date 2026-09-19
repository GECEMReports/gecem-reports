from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.equipment import Equipment
from app.tenancy.middleware import current_tenant_id

router = APIRouter(prefix="/ai", tags=["ai"])


class FallaAgentRequest(BaseModel):
    equipment_id: str
    diagnostico_ia: str
    descripcion_mecanico: str


class FallaAgentResponse(BaseModel):
    necesita_mas_info: bool
    pregunta_seguimiento: str | None = None
    falla_estructurada: dict | None = None


@router.post("/estructurar-falla", response_model=FallaAgentResponse)
async def estructurar_falla(req: FallaAgentRequest, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify equipment belongs to tenant
    result = await db.execute(
        select(Equipment).where(
            Equipment.id == req.equipment_id,
            Equipment.tenant_id == tenant_id,
        )
    )
    equipment = result.scalar_one_or_none()
    if not equipment:
        raise HTTPException(404, "Equipment not found")

    # Run falla agent
    from app.agents.falla_agent import falla_agent

    initial_state = {
        "messages": [],
        "diagnostico_ia": req.diagnostico_ia,
        "descripcion_mecanico": req.descripcion_mecanico,
        "marca": equipment.brand,
        "modelo": equipment.model,
        "horas": equipment.hours,
        "falla_estructurada": {},
        "necesita_mas_info": False,
        "pregunta_seguimiento": "",
    }

    final_state = await falla_agent.ainvoke(initial_state)

    if final_state.get("necesita_mas_info"):
        return FallaAgentResponse(
            necesita_mas_info=True,
            pregunta_seguimiento=final_state.get("pregunta_seguimiento", ""),
        )

    return FallaAgentResponse(
        necesita_mas_info=False,
        falla_estructurada=final_state.get("falla_estructurada", {}),
    )
