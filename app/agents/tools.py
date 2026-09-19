import csv
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.equipment import Equipment
from app.models.report import Report

_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "fallas_historicas.csv"


def _load_failures_from_csv() -> list[dict]:
    rows = []
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "marca": row["marca"].strip(),
                "modelo": row["modelo"].strip(),
                "parte": row["parte"].strip(),
                "pieza": row["pieza"].strip(),
                "falla": row["falla"].strip(),
                "solution": row["solucion_propuesta"].strip(),
                "status": row["estatus"].strip(),
            })
    return rows


_ALL_FAILURES = _load_failures_from_csv()


async def search_equipment_history(equipment_id: str) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(Equipment).where(Equipment.id == uuid.UUID(equipment_id))
        )
        equipment = result.scalar_one_or_none()
        if not equipment:
            return {"error": "Equipment not found"}

        reports_result = await session.execute(
            select(Report).where(Report.equipment_id == equipment_id)
        )
        reports = reports_result.scalars().all()

        return {
            "equipment": {
                "brand": equipment.brand,
                "model": equipment.model,
                "serial_number": equipment.serial_number,
                "type": equipment.equipment_type,
                "hours": equipment.hours,
                "year": equipment.year,
            },
            "history": [
                {
                    "title": r.title,
                    "type": r.report_type,
                    "symptoms": r.symptoms,
                    "diagnosis": r.diagnosis,
                    "created_at": str(r.created_at),
                }
                for r in reports
            ],
        }


def get_common_failures(brand: str, model: str) -> dict:
    brand_lower = brand.strip().lower()
    model_lower = model.strip().lower()

    matched = [
        {
            "failure": f"{r['parte']} - {r['pieza']}: {r['falla']}",
            "symptoms": r["falla"],
            "solution": r["solution"],
            "status": r["status"],
        }
        for r in _ALL_FAILURES
        if r["marca"].lower() == brand_lower and r["modelo"].lower() == model_lower
    ]

    return {"brand": brand, "model": model, "common_failures": matched}
