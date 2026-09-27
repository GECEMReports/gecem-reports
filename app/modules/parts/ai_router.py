from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.parts import service as parts_service
from app.modules.parts.schemas import (
    ConfirmarRefaccionesRequest,
    SugerirRefaccionesRequest,
    SugerirRefaccionesResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/sugerir-refacciones", response_model=SugerirRefaccionesResponse)
async def sugerir_refacciones(
    req: SugerirRefaccionesRequest,
    db: AsyncSession = Depends(get_db),
):
    return await parts_service.suggest_refacciones(db, req)


@router.post("/confirmar-refacciones")
async def confirmar_refacciones(
    req: ConfirmarRefaccionesRequest,
    db: AsyncSession = Depends(get_db),
):
    return await parts_service.confirm_refacciones(db, req)
