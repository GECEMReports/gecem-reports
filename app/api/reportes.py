import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.equipment import Equipment
from app.models.falla import (
    Falla,
    PasoFoto,
    PasoReparacion,
    ProcedimientoReparacion,
    Refaccion,
    ReporteCliente,
)
from app.schemas.reparacion import ReporteClienteResponse
from app.tenancy.middleware import current_tenant_id

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.post("/generar/{falla_id}", response_model=ReporteClienteResponse)
async def generar_reporte(falla_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Get falla
    falla_result = await db.execute(
        select(Falla).where(Falla.id == falla_id, Falla.tenant_id == tenant_id)
    )
    falla = falla_result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    # Get equipment
    eq_result = await db.execute(
        select(Equipment).where(Equipment.id == falla.equipment_id, Equipment.tenant_id == tenant_id)
    )
    equipment = eq_result.scalar_one_or_none()

    # Get refacciones
    ref_result = await db.execute(
        select(Refaccion).where(Refaccion.falla_id == falla_id, Refaccion.tenant_id == tenant_id)
    )
    refacciones = ref_result.scalars().all()

    # Get procedimiento with pasos
    proc_result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.falla_id == falla_id, ProcedimientoReparacion.tenant_id == tenant_id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    procedimiento = proc_result.scalar_one_or_none()

    pasos_list = []
    fotos_por_paso = {}
    tiempo_total = 0.0
    if procedimiento:
        tiempo_total = procedimiento.tiempo_total_horas
        for paso in procedimiento.pasos:
            pasos_list.append({
                "numero_paso": paso.numero_paso,
                "descripcion": paso.descripcion,
                "tiempo_minutos": paso.tiempo_minutos,
            })
            if paso.fotos:
                fotos_por_paso[paso.numero_paso] = [f.filepath for f in paso.fotos]

    # Run reporte agent
    from app.agents.reporte_agent import reporte_agent

    initial_state = {
        "messages": [],
        "falla_id": str(falla.id),
        "parte": falla.parte,
        "pieza": falla.pieza,
        "descripcion": falla.descripcion,
        "causa_raiz": falla.causa_raiz or "",
        "marca": equipment.brand if equipment else "",
        "modelo": equipment.model if equipment else "",
        "horas": equipment.hours if equipment else 0,
        "refacciones": [
            {"nombre": r.nombre, "cantidad": r.cantidad}
            for r in refacciones
        ],
        "pasos": pasos_list,
        "tiempo_total": tiempo_total,
        "contenido": {},
    }

    final_state = await reporte_agent.ainvoke(initial_state)
    contenido = final_state.get("contenido", {})

    # Generate PDF
    from app.utils.reporte_pdf import generar_reporte_cliente_pdf

    falla_dict = {
        "parte": falla.parte,
        "pieza": falla.pieza,
        "descripcion": falla.descripcion,
        "causa_raiz": falla.causa_raiz,
    }
    eq_dict = {
        "brand": equipment.brand if equipment else "",
        "model": equipment.model if equipment else "",
        "serial_number": equipment.serial_number if equipment else "",
        "hours": equipment.hours if equipment else 0,
        "year": equipment.year if equipment else None,
    }
    ref_list = [
        {"nombre": r.nombre, "cantidad": r.cantidad}
        for r in refacciones
    ]

    pdf_buffer = generar_reporte_cliente_pdf(
        falla_dict, eq_dict, contenido, ref_list, pasos_list, fotos_por_paso
    )

    # Save report
    contenido_text = "\n\n".join(
        f"## {k.replace('_', ' ').title()}\n{v}"
        for k, v in contenido.items()
        if v
    )

    reporte = ReporteCliente(
        tenant_id=tenant_id,
        falla_id=falla_id,
        contenido=contenido_text,
    )
    db.add(reporte)
    await db.commit()
    await db.refresh(reporte)

    return reporte


@router.get("/{reporte_id}", response_model=ReporteClienteResponse)
async def get_reporte(reporte_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(ReporteCliente).where(
            ReporteCliente.id == reporte_id,
            ReporteCliente.tenant_id == tenant_id,
        )
    )
    reporte = result.scalar_one_or_none()
    if not reporte:
        raise HTTPException(404, "Reporte not found")
    return reporte


@router.get("/{reporte_id}/pdf")
async def download_reporte_pdf(reporte_id: uuid.UUID, token: str | None = None, db: AsyncSession = Depends(get_db)):
    # Resolve tenant
    tenant_id = current_tenant_id.get()
    if not tenant_id and token:
        from app.utils.auth import decode_access_token
        payload = decode_access_token(token)
        if payload and payload.get("tenant_id"):
            tenant_id = uuid.UUID(payload["tenant_id"])
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Get reporte
    rep_result = await db.execute(
        select(ReporteCliente).where(
            ReporteCliente.id == reporte_id,
            ReporteCliente.tenant_id == tenant_id,
        )
    )
    reporte = rep_result.scalar_one_or_none()
    if not reporte:
        raise HTTPException(404, "Reporte not found")

    # Get falla
    falla_result = await db.execute(
        select(Falla).where(Falla.id == reporte.falla_id, Falla.tenant_id == tenant_id)
    )
    falla = falla_result.scalar_one_or_none()

    # Get equipment
    equipment = None
    if falla:
        eq_result = await db.execute(
            select(Equipment).where(Equipment.id == falla.equipment_id, Equipment.tenant_id == tenant_id)
        )
        equipment = eq_result.scalar_one_or_none()

    # Get refacciones
    ref_result = await db.execute(
        select(Refaccion).where(Refaccion.falla_id == reporte.falla_id, Refaccion.tenant_id == tenant_id)
    )
    refacciones = ref_result.scalars().all()

    # Get pasos
    proc_result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.falla_id == reporte.falla_id, ProcedimientoReparacion.tenant_id == tenant_id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    procedimiento = proc_result.scalar_one_or_none()

    pasos_list = []
    fotos_por_paso = {}
    if procedimiento:
        for paso in procedimiento.pasos:
            pasos_list.append({
                "numero_paso": paso.numero_paso,
                "descripcion": paso.descripcion,
                "tiempo_minutos": paso.tiempo_minutos,
            })
            if paso.fotos:
                fotos_por_paso[paso.numero_paso] = [f.filepath for f in paso.fotos]

    # Parse contenido back
    contenido = {}
    if reporte.contenido:
        for section in reporte.contenido.split("## "):
            if section.strip():
                lines = section.strip().split("\n", 1)
                key = lines[0].lower().replace(" ", "_")
                val = lines[1].strip() if len(lines) > 1 else ""
                contenido[key] = val

    from app.utils.reporte_pdf import generar_reporte_cliente_pdf

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
        "year": equipment.year if equipment else None,
    }
    ref_list = [{"nombre": r.nombre, "cantidad": r.cantidad} for r in refacciones]

    pdf_buffer = generar_reporte_cliente_pdf(
        falla_dict, eq_dict, contenido, ref_list, pasos_list, fotos_por_paso
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="reporte-{reporte_id}.pdf"'},
    )
