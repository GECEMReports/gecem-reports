import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.reports import service as reports_service
from app.modules.reports.schemas import ReporteClienteResponse

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.post("/generar/{falla_id}", response_model=ReporteClienteResponse)
async def generar_reporte(falla_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await reports_service.generate_report(db, falla_id)


@router.get("/{reporte_id}", response_model=ReporteClienteResponse)
async def get_reporte(reporte_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    reporte = await reports_service.get_report(db, reporte_id)
    if not reporte:
        raise HTTPException(404, "Reporte not found")
    return reporte


@router.get("/{reporte_id}/pdf")
async def download_reporte_pdf(reporte_id: uuid.UUID, token: str | None = None, db: AsyncSession = Depends(get_db)):
    return await reports_service.generate_report_pdf(db, reporte_id, token)
