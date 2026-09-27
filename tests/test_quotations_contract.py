"""ETAPA 0 (Quotations) — Tests de contrato y regresion del dominio Cotizaciones.

Congela el comportamiento ACTUAL de:
- POST/GET /api/cotizaciones/, GET /{id}, GET /{id}/pdf
SIN cambiar codigo productivo. Sin LLM (este dominio no usa agentes).

Hallazgos congelados aqui (deuda documentada, NO corregida):
- `uuid.UUID(req.falla_id)` sin validar: falla_id malformado -> 500.
- GET /{id} SIN tenant responde 404 (sin check 400).
- `agents/cotizacion_agent.py` existe pero NINGUN endpoint lo invoca;
  `GenerarCotizacionRequest`/`CotizacionAgentResponse` sin uso (código muerto).
- `equipment_id` se copia de la Falla (el request no lo envía ni se valida).
- create_procedimiento acepta cotizacion_id sin verificar existencia
  (la FK de DB lo rechaza si no existe).

Dependencias actuales (NO migrar en ETAPA 0):
- Falla: query directa (temporal, Failures no extrae Cotizaciones).
- Equipment: via equipment service (ya modularizado).
- Refacciones: via parts service (ya modularizado).
"""

import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from app.database import async_session
from app.models.base import TenantModel
from app.modules.quotations.models import Cotizacion
from app.modules.equipment.models import Equipment

from conftest import tenant_headers

pytestmark = pytest.mark.anyio

COTIZACION_RESPONSE_KEYS = {
    "id",
    "falla_id",
    "equipment_id",
    "tipo",
    "subtotal_refacciones",
    "mano_de_obra",
    "total",
    "moneda",
    "notas",
    "fecha_vencimiento",
    "status",
    "created_at",
}


@pytest.fixture
async def tenant_b(test_db):
    async with async_session() as session:
        tenant = TenantModel(name="Tenant B", slug=f"qb-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        equipment = Equipment(
            tenant_id=tenant.id,
            brand="Komatsu",
            model="PC200",
            serial_number=f"SN-QB-{uuid.uuid4().hex[:8]}",
            equipment_type="loader",
        )
        session.add(equipment)
        await session.flush()
        await session.commit()
        data = {"tenant_id": tenant.id, "equipment_id": equipment.id}
    yield data


@pytest.fixture
async def falla_a(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/fallas/",
        json={
            "equipment_id": str(test_db["equipment_id"]),
            "parte": "Motor",
            "pieza": "Inyector",
            "descripcion": "falla para cotizar",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def create_cotizacion(client, headers, falla_id, **overrides):
    payload = {"falla_id": str(falla_id), "subtotal_refacciones": 1000.0, "mano_de_obra": 777.0}
    payload.update(overrides)
    return await client.post("/api/cotizaciones/", json=payload, headers=headers)


def pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# 1. Crear cotización ----------------------------------------------------------------
async def test_create_cotizacion_valid(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_cotizacion(
        client, headers, falla_a["id"], moneda="MXN", notas="nota de prueba"
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == COTIZACION_RESPONSE_KEYS
    assert body["falla_id"] == falla_a["id"]
    assert body["equipment_id"] == str(test_db["equipment_id"])
    assert body["tipo"] == "manual"
    assert body["subtotal_refacciones"] == 1000.0
    assert body["mano_de_obra"] == 777.0
    assert body["total"] == 1777.0
    assert body["status"] == "borrador"
    assert body["notas"] == "nota de prueba"
    venc = datetime.fromisoformat(body["fecha_vencimiento"])
    expected = datetime.now(timezone.utc) + timedelta(days=30)
    assert abs((venc - expected).total_seconds()) < 120

    async with async_session() as session:
        result = await session.execute(
            select(Cotizacion).where(Cotizacion.id == uuid.UUID(body["id"]))
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.tenant_id == test_db["tenant_id"]
    assert row.equipment_id == test_db["equipment_id"]
    assert row.total == 1777.0


async def test_create_cotizacion_without_tenant_returns_400(client, test_db, falla_a):
    res = await create_cotizacion(client, {}, falla_a["id"])
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


async def test_create_cotizacion_unknown_falla_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_cotizacion(client, headers, str(uuid.uuid4()))
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


async def test_create_cotizacion_malformed_falla_id_raises(client, test_db):
    # Comportamiento real: uuid.UUID() sin try -> propaga (500 en prod).
    headers = tenant_headers(test_db["tenant_id"])
    with pytest.raises(ValueError):
        await create_cotizacion(client, headers, "no-es-un-uuid")


async def test_create_cotizacion_missing_falla_id_returns_422(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/cotizaciones/", json={"mano_de_obra": 10}, headers=headers
    )
    assert res.status_code == 422


# 2. Listar cotizaciones ------------------------------------------------------------------
async def test_list_cotizaciones_isolated(client, test_db, tenant_b, falla_a):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])
    cot_a = await create_cotizacion(client, headers_a, falla_a["id"])
    assert cot_a.status_code == 200

    falla_b = (
        await client.post(
            "/api/fallas/",
            json={
                "equipment_id": str(tenant_b["equipment_id"]),
                "parte": "M", "pieza": "P", "descripcion": "d",
            },
            headers=headers_b,
        )
    ).json()
    cot_b = await create_cotizacion(client, headers_b, falla_b["id"])
    assert cot_b.status_code == 200

    list_a = (await client.get("/api/cotizaciones/", headers=headers_a)).json()
    list_b = (await client.get("/api/cotizaciones/", headers=headers_b)).json()
    assert [c["id"] for c in list_a] == [cot_a.json()["id"]]
    assert [c["id"] for c in list_b] == [cot_b.json()["id"]]


async def test_list_cotizaciones_filter_and_order(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    first = await create_cotizacion(client, headers, falla_a["id"], mano_de_obra=10)
    second = await create_cotizacion(client, headers, falla_a["id"], mano_de_obra=20)
    other_falla = (
        await client.post(
            "/api/fallas/",
            json={
                "equipment_id": str(test_db["equipment_id"]),
                "parte": "M", "pieza": "P2", "descripcion": "d2",
            },
            headers=headers,
        )
    ).json()
    other = await create_cotizacion(client, headers, other_falla["id"], mano_de_obra=30)

    res = await client.get("/api/cotizaciones/", headers=headers)
    assert res.status_code == 200
    assert [c["id"] for c in res.json()] == [
        other.json()["id"], second.json()["id"], first.json()["id"]
    ]

    filtered = await client.get(
        "/api/cotizaciones/", params={"falla_id": falla_a["id"]}, headers=headers
    )
    assert filtered.status_code == 200
    ids = [c["id"] for c in filtered.json()]
    assert ids == [second.json()["id"], first.json()["id"]]

    empty = await client.get(
        "/api/cotizaciones/", params={"falla_id": str(uuid.uuid4())}, headers=headers
    )
    assert empty.json() == []


async def test_list_cotizaciones_without_tenant_returns_400(client, test_db):
    res = await client.get("/api/cotizaciones/")
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


# 3. Obtener cotización -----------------------------------------------------------------------
async def test_get_own_cotizacion(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_cotizacion(client, headers, falla_a["id"])
    res = await client.get(f"/api/cotizaciones/{created.json()['id']}", headers=headers)
    assert res.status_code == 200
    assert set(res.json().keys()) == COTIZACION_RESPONSE_KEYS


async def test_get_unknown_cotizacion_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(f"/api/cotizaciones/{uuid.uuid4()}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Cotizacion not found"


async def test_get_cotizacion_without_tenant_returns_404(client, test_db, falla_a):
    # Comportamiento real: sin check 400 (404, no 400).
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_cotizacion(client, headers, falla_a["id"])
    res = await client.get(f"/api/cotizaciones/{created.json()['id']}")
    assert res.status_code == 404
    assert res.json()["detail"] == "Cotizacion not found"


async def test_get_other_tenant_cotizacion_returns_404(client, test_db, tenant_b, falla_a):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])
    created = await create_cotizacion(client, headers_a, falla_a["id"])
    res = await client.get(f"/api/cotizaciones/{created.json()['id']}", headers=headers_b)
    assert res.status_code == 404


# 4. PDF --------------------------------------------------------------------------------------------
async def _cotizacion_con_refacciones(client, headers, falla_id):
    await client.post(
        f"/api/fallas/{falla_id}/refacciones",
        json={"nombre": "InyectorTest", "cantidad": 2, "precio_unitario": 500.0},
        headers=headers,
    )
    cot = await create_cotizacion(
        client, headers, falla_id, subtotal_refacciones=1000.0, mano_de_obra=777.0
    )
    assert cot.status_code == 200
    return cot.json()


async def test_cotizacion_pdf_contains_data(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    cot = await _cotizacion_con_refacciones(client, headers, falla_a["id"])

    res = await client.get(f"/api/cotizaciones/{cot['id']}/pdf", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content[:5] == b"%PDF-"
    text = pdf_text(res.content)
    assert "777" in text
    assert "1777" in text.replace(",", "").replace(" ", "")
    assert "InyectorTest" in text


async def test_cotizacion_pdf_without_tenant_returns_400(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    cot = await create_cotizacion(client, headers, falla_a["id"])
    res = await client.get(f"/api/cotizaciones/{cot.json()['id']}/pdf")
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


async def test_cotizacion_pdf_unknown_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(f"/api/cotizaciones/{uuid.uuid4()}/pdf", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Cotizacion not found"


async def test_cotizacion_pdf_other_tenant_returns_404(client, test_db, tenant_b, falla_a):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])
    cot = await create_cotizacion(client, headers_a, falla_a["id"])
    res = await client.get(f"/api/cotizaciones/{cot.json()['id']}/pdf", headers=headers_b)
    assert res.status_code == 404


async def test_cotizacion_pdf_differs_between_cotizaciones(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    cot1 = await create_cotizacion(client, headers, falla_a["id"], mano_de_obra=100)
    cot2 = await create_cotizacion(client, headers, falla_a["id"], mano_de_obra=200)
    pdf1 = await client.get(f"/api/cotizaciones/{cot1.json()['id']}/pdf", headers=headers)
    pdf2 = await client.get(f"/api/cotizaciones/{cot2.json()['id']}/pdf", headers=headers)
    assert pdf1.content != pdf2.content
    assert "100" in pdf_text(pdf1.content)
    assert "200" in pdf_text(pdf2.content)


# 6. Consumidor aguas abajo: Repairs ------------------------------------------------------------------
async def test_procedimiento_uses_cotizacion(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    cot = await create_cotizacion(client, headers, falla_a["id"])
    res = await client.post(
        "/api/reparaciones/",
        json={
            "equipment_id": str(test_db["equipment_id"]),
            "falla_id": falla_a["id"],
            "cotizacion_id": cot.json()["id"],
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["cotizacion_id"] == cot.json()["id"]
    assert res.json()["falla_id"] == falla_a["id"]


async def test_procedimiento_unknown_cotizacion_id_fails(client, test_db, falla_a):
    # Comportamiento real: sin verificacion previa; la FK de DB lo rechaza.
    headers = tenant_headers(test_db["tenant_id"])
    with pytest.raises(Exception):
        await client.post(
            "/api/reparaciones/",
            json={
                "equipment_id": str(test_db["equipment_id"]),
                "falla_id": falla_a["id"],
                "cotizacion_id": str(uuid.uuid4()),
            },
            headers=headers,
        )
