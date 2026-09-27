"""Parts domain service (thin).

Encapsulates the Refacciones operations, moved verbatim from the former
`app/api/fallas/__init__.py` (list/create) and `app/api/ai/refacciones.py`
(suggest/confirm) endpoints. No logic changes.

TEMPORAL DEPENDENCY (documented): list/create/suggest/confirm verify the
parent Falla by reading `app.models.falla` directly. It will be switched
to a Failures port once Failures is modularized. Failures itself is NOT
modularized in this stage.

Equipment is consumed exclusively through the Equipment module's public
service (`get_equipment_or_404`).
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.failures.models import Falla  # TEMPORAL: ver docstring del modulo
from app.modules.equipment.service import get_equipment_or_404
from app.modules.parts.models import Refaccion
from app.modules.parts.schemas import (
    ConfirmarRefaccionesRequest,
    RefaccionCreate,
    SugerirRefaccionesRequest,
    SugerirRefaccionesResponse,
)
from app.tenancy.middleware import current_tenant_id


async def list_refacciones(db: AsyncSession, falla_id: uuid.UUID) -> list[Refaccion]:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Refaccion)
        .where(Refaccion.falla_id == falla_id, Refaccion.tenant_id == tenant_id)
        .order_by(Refaccion.created_at.desc())
    )
    return result.scalars().all()


async def list_refacciones_for_falla(
    db: AsyncSession, falla_id: uuid.UUID
) -> list[Refaccion]:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Refaccion).where(
            Refaccion.falla_id == falla_id, Refaccion.tenant_id == tenant_id
        )
    )
    return result.scalars().all()


async def create_refaccion(
    db: AsyncSession, falla_id: uuid.UUID, req: RefaccionCreate
) -> Refaccion:
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

    refaccion = Refaccion(
        tenant_id=tenant_id,
        falla_id=falla_id,
        nombre=req.nombre,
        numero_parte=req.numero_parte,
        cantidad=req.cantidad,
        precio_unitario=req.precio_unitario,
        moneda=req.moneda,
        proveedor=req.proveedor,
        precio_confirmado=req.precio_confirmado,
    )
    db.add(refaccion)
    await db.commit()
    await db.refresh(refaccion)
    return refaccion


async def suggest_refacciones(
    db: AsyncSession, req: SugerirRefaccionesRequest
) -> SugerirRefaccionesResponse:
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
    equipment = await get_equipment_or_404(db, falla.equipment_id)

    # Run refacciones agent
    from app.modules.parts.agent import refacciones_agent

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


async def confirm_refacciones(
    db: AsyncSession, req: ConfirmarRefaccionesRequest
) -> dict:
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


__all__ = [
    "confirm_refacciones",
    "create_refaccion",
    "list_refacciones",
    "list_refacciones_for_falla",
    "suggest_refacciones",
]
