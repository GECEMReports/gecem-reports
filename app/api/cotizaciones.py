import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.equipment import Equipment
from app.models.falla import Cotizacion, Falla, Refaccion
from app.schemas.cotizacion import (
    CotizacionAgentResponse,
    CotizacionCreate,
    CotizacionResponse,
    GenerarCotizacionRequest,
)
from app.tenancy.middleware import current_tenant_id

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


@router.post("/", response_model=CotizacionResponse)
async def create_cotizacion(req: CotizacionCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    falla_uuid = uuid.UUID(req.falla_id)
    falla_result = await db.execute(
        select(Falla).where(Falla.id == falla_uuid, Falla.tenant_id == tenant_id)
    )
    falla = falla_result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

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


@router.get("/", response_model=list[CotizacionResponse])
async def list_cotizaciones(falla_id: str | None = None, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    query = select(Cotizacion).where(Cotizacion.tenant_id == tenant_id)
    if falla_id:
        query = query.where(Cotizacion.falla_id == falla_id)
    query = query.order_by(Cotizacion.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{cotizacion_id}", response_model=CotizacionResponse)
async def get_cotizacion(cotizacion_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Cotizacion).where(
            Cotizacion.id == cotizacion_id,
            Cotizacion.tenant_id == tenant_id,
        )
    )
    cotizacion = result.scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(404, "Cotizacion not found")
    return cotizacion


@router.get("/{cotizacion_id}/pdf")
async def download_cotizacion_pdf(cotizacion_id: uuid.UUID, token: str | None = None, db: AsyncSession = Depends(get_db)):
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

    # Get falla
    falla_result = await db.execute(
        select(Falla).where(Falla.id == cotizacion.falla_id, Falla.tenant_id == tenant_id)
    )
    falla = falla_result.scalar_one_or_none()

    # Get equipment
    eq_result = await db.execute(
        select(Equipment).where(Equipment.id == cotizacion.equipment_id, Equipment.tenant_id == tenant_id)
    )
    equipment = eq_result.scalar_one_or_none()

    # Get refacciones
    ref_result = await db.execute(
        select(Refaccion).where(Refaccion.falla_id == cotizacion.falla_id, Refaccion.tenant_id == tenant_id)
    )
    refacciones = ref_result.scalars().all()

    from app.utils.pdf import generar_cotizacion_pdf

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
