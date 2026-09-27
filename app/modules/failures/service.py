"""Failures domain service (thin).

Encapsulates the Fallas operations, moved verbatim from the former
`app/api/fallas/__init__.py` router and `app/api/ai/falla.py` endpoint.
No logic changes.

Equipment is consumed exclusively through the Equipment module's public
service (`get_equipment_or_404`).
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.equipment.service import get_equipment_or_404
from app.modules.failures.models import Falla, FallaFoto
from app.modules.failures.schemas import (
    FallaAgentResponse,
    FallaCreate,
    FallaResponse,
    FallaUpdate,
)
from app.tenancy.middleware import current_tenant_id

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "media" / "fallas"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def create_falla(db: AsyncSession, req: FallaCreate) -> Falla:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Convert string IDs to UUID
    equipment_uuid = uuid.UUID(req.equipment_id)
    diagnosis_uuid = uuid.UUID(req.diagnosis_id) if req.diagnosis_id else None

    # Verify equipment belongs to tenant
    await get_equipment_or_404(db, equipment_uuid)

    falla = Falla(
        tenant_id=tenant_id,
        equipment_id=equipment_uuid,
        diagnosis_id=diagnosis_uuid,
        parte=req.parte,
        pieza=req.pieza,
        descripcion=req.descripcion,
        causa_raiz=req.causa_raiz,
        prioridad=req.prioridad,
        notas=req.notas,
    )
    db.add(falla)
    await db.commit()
    await db.refresh(falla)

    # Reload with fotos relationship
    result = await db.execute(
        select(Falla).where(Falla.id == falla.id).options(selectinload(Falla.fotos))
    )
    return result.scalar_one()


async def list_fallas(
    db: AsyncSession, equipment_id: str | None = None
) -> list[Falla]:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    query = select(Falla).where(Falla.tenant_id == tenant_id).options(selectinload(Falla.fotos))
    if equipment_id:
        query = query.where(Falla.equipment_id == equipment_id)
    query = query.order_by(Falla.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_falla(db: AsyncSession, falla_id: uuid.UUID) -> Falla | None:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Falla)
        .where(Falla.id == falla_id, Falla.tenant_id == tenant_id)
        .options(selectinload(Falla.fotos))
    )
    return result.scalar_one_or_none()


async def get_falla_or_404(db: AsyncSession, falla_id: uuid.UUID) -> Falla:
    falla = await get_falla(db, falla_id)
    if not falla:
        raise HTTPException(404, "Falla not found")
    return falla


async def update_falla(
    db: AsyncSession, falla_id: uuid.UUID, req: FallaUpdate
) -> Falla:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Falla)
        .where(Falla.id == falla_id, Falla.tenant_id == tenant_id)
        .options(selectinload(Falla.fotos))
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(falla, field, value)

    await db.commit()
    await db.refresh(falla)
    return falla


async def add_falla_foto(
    db: AsyncSession,
    falla_id: uuid.UUID,
    file: UploadFile,
    descripcion: str | None = None,
) -> dict:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify falla belongs to tenant
    result = await db.execute(
        select(Falla).where(Falla.id == falla_id, Falla.tenant_id == tenant_id)
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    # Save file
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    # Save to DB
    foto = FallaFoto(
        tenant_id=tenant_id,
        falla_id=falla_id,
        filename=filename,
        filepath=str(filepath),
        descripcion=descripcion,
    )
    db.add(foto)
    await db.commit()

    return {"id": foto.id, "filename": filename, "message": "Foto subida"}


async def structure_falla(
    db: AsyncSession,
    equipment_id: str,
    diagnostico_ia: str,
    descripcion_mecanico: str,
) -> FallaAgentResponse:
    from app.modules.failures.agent import falla_agent

    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify equipment belongs to tenant
    equipment = await get_equipment_or_404(db, equipment_id)

    initial_state = {
        "messages": [],
        "diagnostico_ia": diagnostico_ia,
        "descripcion_mecanico": descripcion_mecanico,
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


__all__ = [
    "FallaResponse",
    "add_falla_foto",
    "create_falla",
    "get_falla",
    "get_falla_or_404",
    "list_fallas",
    "structure_falla",
    "update_falla",
]
