from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.failures import service as failures_service
from app.modules.failures.schemas import FallaAgentRequest, FallaAgentResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/estructurar-falla", response_model=FallaAgentResponse)
async def estructurar_falla(req: FallaAgentRequest, db: AsyncSession = Depends(get_db)):
    return await failures_service.structure_falla(
        db, req.equipment_id, req.diagnostico_ia, req.descripcion_mecanico
    )
