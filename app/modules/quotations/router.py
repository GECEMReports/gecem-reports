import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.quotations import service as quotations_service
from app.modules.quotations.schemas import CotizacionCreate, CotizacionResponse

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


@router.post("/", response_model=CotizacionResponse)
async def create_cotizacion(req: CotizacionCreate, db: AsyncSession = Depends(get_db)):
    return await quotations_service.create_quotation(db, req)


@router.get("/", response_model=list[CotizacionResponse])
async def list_cotizaciones(falla_id: str | None = None, db: AsyncSession = Depends(get_db)):
    return await quotations_service.list_quotations(db, falla_id)


@router.get("/{cotizacion_id}", response_model=CotizacionResponse)
async def get_cotizacion(cotizacion_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cotizacion = await quotations_service.get_quotation(db, cotizacion_id)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion not found")
    return cotizacion


@router.get("/{cotizacion_id}/pdf")
async def download_cotizacion_pdf(cotizacion_id: uuid.UUID, token: str | None = None, db: AsyncSession = Depends(get_db)):
    return await quotations_service.generate_quotation_pdf(db, cotizacion_id, token)
