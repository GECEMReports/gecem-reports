import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.equipment import Equipment
from app.models.falla import Falla, Refaccion
from app.schemas.refacciones import (
    ConfirmarRefaccionesRequest,
    SugerirRefaccionesRequest,
    SugerirRefaccionesResponse,
)
from app.tenancy.middleware import current_tenant_id

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/sugerir-refacciones", response_model=SugerirRefaccionesResponse)
async def sugerir_refacciones(
    req: SugerirRefaccionesRequest,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Get falla with equipment
    result = await db.execute(
        select(Falla)
        .where(Falla.id == req.falla_id, Falla.tenant_id == tenant_id)
        .options(selectinload(Falla.fotos))
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    # Get equipment
    eq_result = await db.execute(
        select(Equipment).where(
            Equipment.id == falla.equipment_id,
            Equipment.tenant_id == tenant_id,
        )
    )
    equipment = eq_result.scalar_one_or_none()
    if not equipment:
        raise HTTPException(404, "Equipment not found")

    # Run refacciones agent
    from app.agents.refacciones_agent import refacciones_agent

    initial_state = {
        "messages": [],
        "falla_id": str(falla.id),
        "parte": falla.parte,
        "pieza": falla.pieza,
        "descripcion": falla.descripcion,
        "causa_raiz": falla.causa_raiz or "",
        "marca": equipment.brand,
        "modelo": equipment.model,
        "horas": equipment.hours,
        "refacciones": [],
        "notas": "",
    }

    final_state = await refacciones_agent.ainvoke(initial_state)

    return SugerirRefaccionesResponse(
        refacciones=final_state.get("refacciones", []),
        notas=final_state.get("notas", ""),
    )


@router.post("/confirmar-refacciones")
async def confirmar_refacciones(
    req: ConfirmarRefaccionesRequest,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify falla belongs to tenant
    result = await db.execute(
        select(Falla).where(Falla.id == req.falla_id, Falla.tenant_id == tenant_id)
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    # Save refacciones
    saved = []
    for ref in req.refacciones:
        refaccion = Refaccion(
            tenant_id=tenant_id,
            falla_id=uuid.UUID(req.falla_id),
            nombre=ref.nombre,
            numero_parte=ref.numero_parte,
            cantidad=ref.cantidad,
            precio_unitario=ref.precio_unitario,
            moneda=ref.moneda,
            precio_confirmado=ref.precio_confirmado,
            editado_por_mecanico=ref.editado_por_mecanico,
            status="aprobada" if ref.precio_confirmado else "sugerida",
        )
        db.add(refaccion)
        saved.append(refaccion)

    await db.commit()

    return {"message": f"{len(saved)} refacciones guardadas", "count": len(saved)}
