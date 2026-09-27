"""Quotations domain service (thin).

Encapsulates the Cotizaciones operations, moved verbatim from the former
`app/api/cotizaciones.py` router. No logic changes.

Failures is consumed exclusively through the Failures module's public
service (`get_falla_or_404` / `get_falla`). Equipment and Parts are
consumed through their own public services.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equipment.service import get_equipment
from app.modules.failures.service import get_falla, get_falla_or_404
from app.modules.parts.service import list_refacciones_for_falla
from app.modules.quotations.models import Cotizacion
from app.modules.quotations.pdf_service import generar_cotizacion_pdf
from app.modules.quotations.schemas import CotizacionCreate, CotizacionResponse
from app.tenancy.middleware import current_tenant_id


async def create_quotation(db: AsyncSession, req: CotizacionCreate) -> Cotizacion:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    falla_uuid = uuid.UUID(req.falla_id)
    falla = await get_falla_or_404(db, falla_uuid)

    total = req.subtotal_refacciones + req.mano_de_obra
    now = datetime.now(timezone.utc)
    cotizacion = Cotizacion(
        tenant_id=tenant_id,
        falla_id=uuid.UUID(req.falla_id),
        equipment_id=falla.equipment_id,
        tipo=req.tipo,
        subtotal_refacciones=req.subtotal_refacciones,
        mano_de_obra=req.mano_de_obra,
        total=total,
        moneda=req.moneda,
        notas=req.notas,
        fecha_vencimiento=now + timedelta(days=30),
        status="borrador",
    )
    db.add(cotizacion)
    await db.commit()
    await db.refresh(cotizacion)
    return cotizacion


async def list_quotations(
    db: AsyncSession, falla_id: str | None = None
) -> list[Cotizacion]:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    query = select(Cotizacion).where(Cotizacion.tenant_id == tenant_id)
    if falla_id:
        query = query.where(Cotizacion.falla_id == falla_id)
    query = query.order_by(Cotizacion.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_quotation(
    db: AsyncSession, cotizacion_id: uuid.UUID
) -> Cotizacion | None:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Cotizacion).where(
            Cotizacion.id == cotizacion_id,
            Cotizacion.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def get_quotation_or_404(
    db: AsyncSession, cotizacion_id: uuid.UUID
) -> Cotizacion:
    cotizacion = await get_quotation(db, cotizacion_id)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion not found")
    return cotizacion


async def generate_quotation_pdf(
    db: AsyncSession, cotizacion_id: uuid.UUID, token: str | None = None
) -> StreamingResponse:
    # Resolve tenant from query param token or header
    tenant_id = current_tenant_id.get()
    if not tenant_id and token:
        from app.utils.auth import decode_access_token
        payload = decode_access_token(token)
        if payload and payload.get("tenant_id"):
            tenant_id = uuid.UUID(payload["tenant_id"])
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Get cotizacion
    cot_result = await db.execute(
        select(Cotizacion).where(
            Cotizacion.id == cotizacion_id,
            Cotizacion.tenant_id == tenant_id,
        )
    )
    cotizacion = cot_result.scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(404, "Cotizacion not found")

    # Expose the resolved tenant to downstream service calls so the
    # token-based path behaves exactly like the header-based path.
    _token = current_tenant_id.set(tenant_id)
    try:
        # Get falla
        falla = await get_falla(db, cotizacion.falla_id)

        # Get equipment
        equipment = await get_equipment(db, cotizacion.equipment_id)

        # Get refacciones
        refacciones = await list_refacciones_for_falla(db, cotizacion.falla_id)
    finally:
        current_tenant_id.reset(_token)

    falla_dict = {
        "parte": falla.parte if falla else "N/A",
        "pieza": falla.pieza if falla else "N/A",
        "descripcion": falla.descripcion if falla else "",
        "causa_raiz": falla.causa_raiz if falla else "",
    }
    eq_dict = {
        "brand": equipment.brand if equipment else "",
        "model": equipment.model if equipment else "",
        "serial_number": equipment.serial_number if equipment else "",
        "hours": equipment.hours if equipment else 0,
    }
    cot_dict = {
        "subtotal_refacciones": cotizacion.subtotal_refacciones,
        "mano_de_obra": cotizacion.mano_de_obra,
        "total": cotizacion.total,
        "moneda": cotizacion.moneda,
        "status": cotizacion.status,
        "notas": cotizacion.notas,
        "fecha_vencimiento": cotizacion.fecha_vencimiento,
    }
    ref_list = [
        {
            "nombre": r.nombre,
            "numero_parte": r.numero_parte,
            "cantidad": r.cantidad,
            "precio_unitario": r.precio_unitario,
        }
        for r in refacciones
    ]

    buffer = generar_cotizacion_pdf(falla_dict, eq_dict, cot_dict, ref_list)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="cotizacion-{cotizacion_id}.pdf"'},
    )


__all__ = [
    "CotizacionResponse",
    "create_quotation",
    "generate_quotation_pdf",
    "get_quotation",
    "get_quotation_or_404",
    "list_quotations",
]
