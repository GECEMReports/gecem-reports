"""ETAPA 0 (Parts) — Tests de contrato y regresion del dominio Refacciones.

Congela el comportamiento ACTUAL de:
- GET/POST /api/fallas/{falla_id}/refacciones
- POST /api/ai/sugerir-refacciones
- POST /api/ai/confirmar-refacciones
SIN cambiar codigo productivo. LLM siempre mockeado.

Hallazgos congelados aqui (deuda documentada, NO corregida):
- GET refacciones SIN tenant responde 200 [] (sin check 400).
- GET refacciones de falla inexistente responde 200 [] (sin 404).
- confirmar_refacciones NO deduplica: confirmar dos veces duplica filas.
- Excepciones del agente NO se capturan (propagan como 500).
- Schemas de refacciones repartidos entre schemas/falla.py y
  schemas/refacciones.py.
"""

import uuid

import pytest
from sqlalchemy import select

import app.modules.parts.agent as refacciones_agent_module
import app.agents.reporte_agent as reporte_agent_module
from app.database import async_session
from app.models.base import TenantModel
from app.modules.parts.models import Refaccion

from conftest import tenant_headers

pytestmark = pytest.mark.anyio

REFACCION_RESPONSE_KEYS = {
    "id",
    "falla_id",
    "nombre",
    "numero_parte",
    "cantidad",
    "precio_unitario",
    "moneda",
    "proveedor",
    "precio_confirmado",
    "editado_por_mecanico",
    "status",
    "created_at",
}

SUGERIDA_ITEM_KEYS = {
    "nombre",
    "numero_parte",
    "pn_verificado",
    "cantidad",
    "precio_estimado",
    "moneda",
    "prioridad",
    "precio_confirmado",
    "editado_por_mecanico",
}


class StubAgent:
    def __init__(self, final_state=None, error=None):
        self.final_state = final_state
        self.error = error
        self.calls = []

    async def ainvoke(self, payload, config=None):
        self.calls.append({"input": payload, "config": config})
        if self.error is not None:
            raise self.error
        return self.final_state


@pytest.fixture
async def tenant_b(test_db):
    async with async_session() as session:
        tenant = TenantModel(name="Tenant B", slug=f"pb-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        await session.commit()
        data = {"tenant_id": tenant.id}
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
            "descripcion": "falla de prueba parts",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def create_refaccion(client, headers, falla_id, **overrides):
    payload = {"nombre": "Filtro de aceite", "cantidad": 1}
    payload.update(overrides)
    return await client.post(
        f"/api/fallas/{falla_id}/refacciones", json=payload, headers=headers
    )


# 1. Listar refacciones ----------------------------------------------------------------
async def test_list_refacciones_empty(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(f"/api/fallas/{falla_a['id']}/refacciones", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


async def test_list_refacciones_shape_and_values(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    await create_refaccion(
        client, headers, falla_a["id"],
        nombre="Filtro", numero_parte="F-123", cantidad=2,
        precio_unitario=150.5, moneda="MXN", proveedor="ACME",
        precio_confirmado=True,
    )
    await create_refaccion(client, headers, falla_a["id"], nombre="Aceite")

    res = await client.get(f"/api/fallas/{falla_a['id']}/refacciones", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    by_name = {i["nombre"]: i for i in items}
    assert set(by_name.keys()) == {"Filtro", "Aceite"}
    assert set(by_name["Filtro"].keys()) == REFACCION_RESPONSE_KEYS
    assert by_name["Filtro"]["numero_parte"] == "F-123"
    assert by_name["Filtro"]["cantidad"] == 2
    assert by_name["Filtro"]["precio_unitario"] == 150.5
    assert by_name["Filtro"]["moneda"] == "MXN"
    assert by_name["Filtro"]["proveedor"] == "ACME"
    assert by_name["Filtro"]["precio_confirmado"] is True
    assert by_name["Filtro"]["falla_id"] == falla_a["id"]


async def test_list_refacciones_without_tenant_returns_empty(client, test_db, falla_a):
    # Comportamiento real: sin check 400, el filtro tenant=None devuelve [].
    await create_refaccion(
        client, tenant_headers(test_db["tenant_id"]), falla_a["id"], nombre="Filtro"
    )
    res = await client.get(f"/api/fallas/{falla_a['id']}/refacciones")
    assert res.status_code == 200
    assert res.json() == []


async def test_list_refacciones_unknown_falla_returns_empty(client, test_db):
    # Comportamiento real: sin verificacion de existencia (200 [], no 404).
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(
        f"/api/fallas/{uuid.uuid4()}/refacciones", headers=headers
    )
    assert res.status_code == 200
    assert res.json() == []


# 2. Agregar (flujo manual) ----------------------------------------------------------------
async def test_create_refaccion_manual(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_refaccion(
        client, headers, falla_a["id"], nombre="Banda", precio_confirmado=True
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == REFACCION_RESPONSE_KEYS
    assert body["nombre"] == "Banda"
    assert body["falla_id"] == falla_a["id"]
    assert body["status"] == "sugerida"
    assert body["precio_confirmado"] is True
    assert body["editado_por_mecanico"] is False

    async with async_session() as session:
        result = await session.execute(
            select(Refaccion).where(Refaccion.id == uuid.UUID(body["id"]))
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.tenant_id == test_db["tenant_id"]
    assert row.falla_id == uuid.UUID(falla_a["id"])


async def test_create_refaccion_without_tenant_returns_400(client, test_db, falla_a):
    res = await create_refaccion(client, {}, falla_a["id"], nombre="Banda")
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


async def test_create_refaccion_unknown_falla_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_refaccion(client, headers, str(uuid.uuid4()), nombre="Banda")
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


# 3. Sugerir con IA (mockeada) ---------------------------------------------------------------
def patch_refacciones_agent(monkeypatch, final_state=None, error=None):
    stub = StubAgent(final_state, error)
    monkeypatch.setattr(refacciones_agent_module, "refacciones_agent", stub)
    return stub


async def test_sugerir_refacciones_valid(client, test_db, falla_a, monkeypatch):
    stub = patch_refacciones_agent(monkeypatch, {
        "refacciones": [
            {"nombre": "Inyector", "cantidad": 4, "precio_estimado": 1200.0, "moneda": "MXN"}
        ],
        "notas": "verificar compatibilidad",
    })
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/sugerir-refacciones", json={"falla_id": falla_a["id"]}, headers=headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == {"refacciones", "notas"}
    assert body["notas"] == "verificar compatibilidad"
    assert len(body["refacciones"]) == 1
    item = body["refacciones"][0]
    assert set(item.keys()) == SUGERIDA_ITEM_KEYS
    assert item["nombre"] == "Inyector"
    assert item["cantidad"] == 4
    assert len(stub.calls) == 1
    agent_input = stub.calls[0]["input"]
    assert agent_input["falla_id"] == falla_a["id"]
    assert agent_input["parte"] == "Motor"
    assert agent_input["marca"] == "CAT"


async def test_sugerir_refacciones_empty_list(client, test_db, falla_a, monkeypatch):
    patch_refacciones_agent(monkeypatch, {"refacciones": [], "notas": ""})
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/sugerir-refacciones", json={"falla_id": falla_a["id"]}, headers=headers
    )
    assert res.status_code == 200
    assert res.json() == {"refacciones": [], "notas": ""}


async def test_sugerir_refacciones_without_tenant_returns_400(client, test_db, falla_a, monkeypatch):
    stub = patch_refacciones_agent(monkeypatch, {"refacciones": [], "notas": ""})
    res = await client.post(
        "/api/ai/sugerir-refacciones", json={"falla_id": falla_a["id"]}
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"
    assert stub.calls == []


async def test_sugerir_refacciones_unknown_falla_returns_404(client, test_db, monkeypatch):
    stub = patch_refacciones_agent(monkeypatch, {"refacciones": [], "notas": ""})
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/sugerir-refacciones",
        json={"falla_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"
    assert stub.calls == []


async def test_sugerir_refacciones_agent_error_propagates(client, test_db, falla_a, monkeypatch):
    # Comportamiento real: sin try/except, la excepcion propaga (500).
    patch_refacciones_agent(monkeypatch, error=RuntimeError("LLM down"))
    headers = tenant_headers(test_db["tenant_id"])
    with pytest.raises(RuntimeError, match="LLM down"):
        await client.post(
            "/api/ai/sugerir-refacciones",
            json={"falla_id": falla_a["id"]},
            headers=headers,
        )


# 4. Confirmar sugerencias ------------------------------------------------------------------------
async def test_confirmar_refacciones_valid(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/confirmar-refacciones",
        json={
            "falla_id": falla_a["id"],
            "refacciones": [
                {"nombre": "Inyector", "cantidad": 4, "precio_unitario": 1100.0,
                 "precio_confirmado": True, "editado_por_mecanico": True},
                {"nombre": "Filtro", "cantidad": 1, "precio_confirmado": False},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"message": "2 refacciones guardadas", "count": 2}

    listed = (
        await client.get(f"/api/fallas/{falla_a['id']}/refacciones", headers=headers)
    ).json()
    assert len(listed) == 2
    by_name = {i["nombre"]: i for i in listed}
    assert by_name["Inyector"]["status"] == "aprobada"
    assert by_name["Inyector"]["precio_unitario"] == 1100.0
    assert by_name["Inyector"]["editado_por_mecanico"] is True
    assert by_name["Filtro"]["status"] == "sugerida"
    assert all(i["falla_id"] == falla_a["id"] for i in listed)

    async with async_session() as session:
        result = await session.execute(
            select(Refaccion).where(Refaccion.falla_id == uuid.UUID(falla_a["id"]))
        )
        rows = result.scalars().all()
    assert len(rows) == 2
    assert all(r.tenant_id == test_db["tenant_id"] for r in rows)


async def test_confirmar_refacciones_duplicates_on_repeat(client, test_db, falla_a):
    # Comportamiento real: sin deduplicacion (deuda documentada).
    headers = tenant_headers(test_db["tenant_id"])
    payload = {"falla_id": falla_a["id"], "refacciones": [{"nombre": "Banda"}]}
    first = await client.post("/api/ai/confirmar-refacciones", json=payload, headers=headers)
    second = await client.post("/api/ai/confirmar-refacciones", json=payload, headers=headers)
    assert first.json()["count"] == 1
    assert second.json()["count"] == 1
    listed = (
        await client.get(f"/api/fallas/{falla_a['id']}/refacciones", headers=headers)
    ).json()
    assert len(listed) == 2


async def test_confirmar_refacciones_without_tenant_returns_400(client, test_db, falla_a):
    res = await client.post(
        "/api/ai/confirmar-refacciones",
        json={"falla_id": falla_a["id"], "refacciones": [{"nombre": "Banda"}]},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


async def test_confirmar_refacciones_unknown_falla_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/confirmar-refacciones",
        json={"falla_id": str(uuid.uuid4()), "refacciones": [{"nombre": "Banda"}]},
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


# 5. Tenant isolation -------------------------------------------------------------------------------
async def test_tenant_b_isolated_from_tenant_a_parts(client, test_db, tenant_b, falla_a):
    headers_b = tenant_headers(tenant_b["tenant_id"])
    headers_a = tenant_headers(test_db["tenant_id"])
    await create_refaccion(client, headers_a, falla_a["id"], nombre="Filtro")

    # Listar: filtro por tenant -> [] (200, sin 404)
    res_list = await client.get(f"/api/fallas/{falla_a['id']}/refacciones", headers=headers_b)
    assert res_list.status_code == 200
    assert res_list.json() == []

    # Crear sobre falla ajena -> 404
    res_create = await create_refaccion(client, headers_b, falla_a["id"], nombre="X")
    assert res_create.status_code == 404
    assert res_create.json()["detail"] == "Falla not found"

    # Sugerir sobre falla ajena -> 404
    res_sug = await client.post(
        "/api/ai/sugerir-refacciones", json={"falla_id": falla_a["id"]}, headers=headers_b
    )
    assert res_sug.status_code == 404

    # Confirmar sobre falla ajena -> 404
    res_conf = await client.post(
        "/api/ai/confirmar-refacciones",
        json={"falla_id": falla_a["id"], "refacciones": [{"nombre": "X"}]},
        headers=headers_b,
    )
    assert res_conf.status_code == 404

    # Nada persistido para B
    async with async_session() as session:
        result = await session.execute(
            select(Refaccion).where(Refaccion.tenant_id == tenant_b["tenant_id"])
        )
        assert result.scalars().all() == []


# 6. Relaciones ------------------------------------------------------------------------------------------
async def test_refaccion_relations_preserved(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_refaccion(client, headers, falla_a["id"], nombre="Banda")
    ref_id = created.json()["id"]

    async with async_session() as session:
        result = await session.execute(
            select(Refaccion).where(Refaccion.id == uuid.UUID(ref_id))
        )
        row = result.scalar_one()
    assert row.falla_id == uuid.UUID(falla_a["id"])
    assert row.tenant_id == test_db["tenant_id"]


# 7. Consumidores: Cotizaciones / Reportes / Fallas / Equipment ----------------------------------------------
class StubReporteAgent:
    def __init__(self, contenido):
        self.contenido = contenido
        self.calls = []

    async def ainvoke(self, payload, config=None):
        self.calls.append({"input": payload, "config": config})
        return {"contenido": self.contenido}


async def test_consumers_read_refacciones(client, test_db, falla_a, monkeypatch):
    headers = tenant_headers(test_db["tenant_id"])
    await create_refaccion(
        client, headers, falla_a["id"], nombre="Inyector",
        cantidad=2, precio_unitario=500.0, precio_confirmado=True,
    )

    # Quotations: cotizar + PDF leen Refacciones
    cot = await client.post(
        "/api/cotizaciones/",
        json={"falla_id": falla_a["id"], "subtotal_refacciones": 1000.0, "mano_de_obra": 200.0},
        headers=headers,
    )
    assert cot.status_code == 200
    pdf = await client.get(f"/api/cotizaciones/{cot.json()['id']}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-"

    # Reports: generar (agente stub) + PDF leen Refacciones
    stub = StubReporteAgent({
        "resumen_ejecutivo": "ok", "diagnostico": "d", "trabajo_realizado": "t",
        "refacciones_utilizadas": "Inyector x2", "recomendaciones": "r", "garantia": "g",
    })
    monkeypatch.setattr(reporte_agent_module, "reporte_agent", stub)
    rep = await client.post(f"/api/reportes/generar/{falla_a['id']}", headers=headers)
    assert rep.status_code == 200, rep.text
    rpdf = await client.get(f"/api/reportes/{rep.json()['id']}/pdf", headers=headers)
    assert rpdf.status_code == 200
    assert rpdf.headers["content-type"] == "application/pdf"

    # Fallas + Equipment siguen legibles y vinculados
    falla = (await client.get(f"/api/fallas/{falla_a['id']}", headers=headers)).json()
    assert falla["equipment_id"] == str(test_db["equipment_id"])
    refs = (await client.get(f"/api/fallas/{falla_a['id']}/refacciones", headers=headers)).json()
    assert len(refs) == 1 and refs[0]["nombre"] == "Inyector"
    eq = (await client.get(f"/api/equipment/{test_db['equipment_id']}", headers=headers)).json()
    assert eq["id"] == str(test_db["equipment_id"])
