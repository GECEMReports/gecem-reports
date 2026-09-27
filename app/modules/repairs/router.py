import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.repairs import service as repairs_service
from app.modules.repairs.schemas import (
    CompletarProcedimientoRequest,
    PasoCreate,
    PasoFotoResponse,
    PasoResponse,
    ProcedimientoCreate,
    ProcedimientoResponse,
)

router = APIRouter(prefix="/reparaciones", tags=["reparaciones"])


@router.post("/", response_model=ProcedimientoResponse)
async def create_procedimiento(req: ProcedimientoCreate, db: AsyncSession = Depends(get_db)):
    return await repairs_service.create_procedimiento(db, req)


@router.get("/", response_model=list[ProcedimientoResponse])
async def list_procedimientos(
    equipment_id: str | None = None,
    falla_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await repairs_service.list_procedimientos(db, equipment_id, falla_id)


@router.get("/{proc_id}", response_model=ProcedimientoResponse)
async def get_procedimiento(proc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    proc = await repairs_service.get_procedimiento(db, proc_id)
    if not proc:
        raise HTTPException(404, "Procedimiento not found")
    return proc


@router.post("/{proc_id}/pasos", response_model=PasoResponse)
async def add_paso(proc_id: uuid.UUID, req: PasoCreate, db: AsyncSession = Depends(get_db)):
    return await repairs_service.add_paso(db, proc_id, req)


@router.post("/{proc_id}/pasos/{paso_id}/fotos", response_model=PasoFotoResponse)
async def upload_paso_foto(
    proc_id: uuid.UUID,
    paso_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    return await repairs_service.add_paso_foto(db, proc_id, paso_id, file)


@router.patch("/{proc_id}/completar", response_model=ProcedimientoResponse)
async def completar_procedimiento(
    proc_id: uuid.UUID,
    req: CompletarProcedimientoRequest,
    db: AsyncSession = Depends(get_db),
):
    return await repairs_service.complete_procedimiento(db, proc_id, req)
