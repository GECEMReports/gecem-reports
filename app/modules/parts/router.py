import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.parts import service as parts_service
from app.modules.parts.schemas import RefaccionCreate, RefaccionResponse

router = APIRouter(prefix="/fallas", tags=["fallas"])


@router.post("/{falla_id}/refacciones", response_model=RefaccionResponse)
async def create_refaccion(
    falla_id: uuid.UUID, req: RefaccionCreate, db: AsyncSession = Depends(get_db)
):
    return await parts_service.create_refaccion(db, falla_id, req)


@router.get("/{falla_id}/refacciones", response_model=list[RefaccionResponse])
async def list_refacciones(falla_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await parts_service.list_refacciones(db, falla_id)
