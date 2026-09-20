import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.falla import (
    Falla,
    PasoFoto,
    PasoReparacion,
    ProcedimientoReparacion,
)
from app.schemas.reparacion import (
    CompletarProcedimientoRequest,
    PasoCreate,
    PasoFotoResponse,
    PasoResponse,
    ProcedimientoCreate,
    ProcedimientoResponse,
)
from app.tenancy.middleware import current_tenant_id

router = APIRouter(prefix="/reparaciones", tags=["reparaciones"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "media" / "pasos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", response_model=ProcedimientoResponse)
async def create_procedimiento(req: ProcedimientoCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    falla_uuid = uuid.UUID(req.falla_id)
    result = await db.execute(
        select(Falla).where(Falla.id == falla_uuid, Falla.tenant_id == tenant_id)
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    proc = ProcedimientoReparacion(
        tenant_id=tenant_id,
        falla_id=falla_uuid,
        cotizacion_id=uuid.UUID(req.cotizacion_id) if req.cotizacion_id else None,
        notas=req.notas,
    )
    db.add(proc)
    await db.commit()
    await db.refresh(proc)

    # Reload with pasos
    result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.id == proc.id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    return result.scalar_one()


@router.get("/{proc_id}", response_model=ProcedimientoResponse)
async def get_procedimiento(proc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.id == proc_id, ProcedimientoReparacion.tenant_id == tenant_id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(404, "Procedimiento not found")
    return proc


@router.post("/{proc_id}/pasos", response_model=PasoResponse)
async def add_paso(proc_id: uuid.UUID, req: PasoCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify proc belongs to tenant
    result = await db.execute(
        select(ProcedimientoReparacion).where(
            ProcedimientoReparacion.id == proc_id,
            ProcedimientoReparacion.tenant_id == tenant_id,
        )
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(404, "Procedimiento not found")

    # Get next step number
    count_result = await db.execute(
        select(PasoReparacion).where(PasoReparacion.procedimiento_id == proc_id)
    )
    existing = count_result.scalars().all()
    next_num = len(existing) + 1

    paso = PasoReparacion(
        tenant_id=tenant_id,
        procedimiento_id=proc_id,
        numero_paso=next_num,
        descripcion=req.descripcion,
        tiempo_minutos=req.tiempo_minutos,
    )
    db.add(paso)
    await db.commit()
    await db.refresh(paso)
    return paso


@router.post("/{proc_id}/pasos/{paso_id}/fotos", response_model=PasoFotoResponse)
async def upload_paso_foto(
    proc_id: uuid.UUID,
    paso_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify paso belongs to proc and tenant
    result = await db.execute(
        select(PasoReparacion).where(
            PasoReparacion.id == paso_id,
            PasoReparacion.procedimiento_id == proc_id,
            PasoReparacion.tenant_id == tenant_id,
        )
    )
    paso = result.scalar_one_or_none()
    if not paso:
        raise HTTPException(404, "Paso not found")

    # Save file
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    foto = PasoFoto(
        tenant_id=tenant_id,
        paso_id=paso_id,
        filename=filename,
        filepath=str(filepath),
    )
    db.add(foto)
    await db.commit()

    return PasoFoto(id=foto.id, filename=filename, filepath=str(filepath))


@router.patch("/{proc_id}/completar", response_model=ProcedimientoResponse)
async def completar_procedimiento(
    proc_id: uuid.UUID,
    req: CompletarProcedimientoRequest,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(ProcedimientoReparacion).where(
            ProcedimientoReparacion.id == proc_id,
            ProcedimientoReparacion.tenant_id == tenant_id,
        )
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(404, "Procedimiento not found")

    proc.status = "completado"
    proc.tiempo_total_horas = req.tiempo_total_horas
    if req.notas:
        proc.notas = req.notas
    await db.commit()

    # Reload with pasos
    result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.id == proc_id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    return result.scalar_one()
