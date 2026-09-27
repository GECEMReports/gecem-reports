import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.failures import service as failures_service
from app.modules.failures.schemas import FallaCreate, FallaResponse, FallaUpdate

router = APIRouter(prefix="/fallas", tags=["fallas"])


@router.post("/", response_model=FallaResponse)
async def create_falla(req: FallaCreate, db: AsyncSession = Depends(get_db)):
    return await failures_service.create_falla(db, req)


@router.get("/", response_model=list[FallaResponse])
async def list_fallas(equipment_id: str | None = None, db: AsyncSession = Depends(get_db)):
    return await failures_service.list_fallas(db, equipment_id)


@router.get("/{falla_id}", response_model=FallaResponse)
async def get_falla(falla_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    falla = await failures_service.get_falla(db, falla_id)
    if not falla:
        raise HTTPException(404, "Falla not found")
    return falla


@router.patch("/{falla_id}", response_model=FallaResponse)
async def update_falla(falla_id: uuid.UUID, req: FallaUpdate, db: AsyncSession = Depends(get_db)):
    return await failures_service.update_falla(db, falla_id, req)


@router.post("/{falla_id}/fotos")
async def upload_foto(
    falla_id: uuid.UUID,
    file: UploadFile = File(...),
    descripcion: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await failures_service.add_falla_foto(db, falla_id, file, descripcion)
