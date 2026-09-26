from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.diagnosis.schemas import DiagnosisRequest, DiagnosisResponse
from app.modules.diagnosis.service import diagnose_equipment as run_diagnosis

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/diagnose", response_model=DiagnosisResponse, response_model_exclude_none=True)
async def diagnose_equipment(
    req: DiagnosisRequest,
    db: AsyncSession = Depends(get_db),
):
    return await run_diagnosis(req, db)
