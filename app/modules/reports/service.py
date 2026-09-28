"""Reports domain service (thin).

Encapsulates the Reportes operations, moved verbatim from the former
`app/api/reportes.py` router. No logic changes.

Direct model reads (Falla, ProcedimientoReparacion, PasoReparacion,
PasoFoto, ReporteCliente) are preserved as-is per ETAPA 1 scope; Equipment
and Parts are consumed through their public services.

DEUDA PRESERVADA (no corregir):
- generar() construye el PDF pero lo descarta (pdf_buffer sin usar).
- La query de procedimiento usa scalar_one_or_none() y rompe con
  MultipleResultsFound si la falla tiene 2+ procedimientos (bug conocido).
"""

import uuid

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.falla import (
    ReporteCliente,
)
from app.modules.equipment.service import get_equipment
from app.modules.failures.models import Falla, FallaFoto  # TEMPORAL: ver docstring
from app.modules.parts.service import list_refacciones_for_falla
from app.modules.repairs.models import (  # TEMPORAL: ver docstring
    PasoFoto,
    PasoReparacion,
    ProcedimientoReparacion,
)
from app.modules.reports.pdf import generar_reporte_cliente_pdf
from app.modules.reports.schemas import ReporteClienteResponse
from app.tenancy.middleware import current_tenant_id


async def generate_report(db: AsyncSession, falla_id: uuid.UUID) -> ReporteCliente:
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
    equipment = await get_equipment(db, falla.equipment_id)

    # Get refacciones
    refacciones = await list_refacciones_for_falla(db, falla_id)

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

    # Generate PDF (buffer discarded, as before)
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


async def get_report(db: AsyncSession, reporte_id: uuid.UUID) -> ReporteCliente | None:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(ReporteCliente).where(
            ReporteCliente.id == reporte_id,
            ReporteCliente.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def get_report_or_404(db: AsyncSession, reporte_id: uuid.UUID) -> ReporteCliente:
    reporte = await get_report(db, reporte_id)
    if not reporte:
        raise HTTPException(404, "Reporte not found")
    return reporte


async def generate_report_pdf(
    db: AsyncSession, reporte_id: uuid.UUID, token: str | None = None
) -> StreamingResponse:
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
        equipment = await get_equipment(db, falla.equipment_id)

    # Get refacciones
    refacciones = await list_refacciones_for_falla(db, reporte.falla_id)

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


__all__ = [
    "ReporteClienteResponse",
    "generate_report",
    "generate_report_pdf",
    "get_report",
    "get_report_or_404",
]
