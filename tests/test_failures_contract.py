"""ETAPA 0 (Failures) — Tests de contrato y regresion del dominio Fallas.

Congela el comportamiento ACTUAL de:
- POST/GET /api/fallas/, GET/PATCH /api/fallas/{id}, POST /{id}/fotos
- POST /api/ai/estructurar-falla
SIN cambiar codigo productivo. LLM siempre mockeado.

Hallazgos congelados aqui (deuda documentada, NO corregida):
- GET /{id} y PATCH /{id} SIN tenant responden 404 (sin check 400).
- FallaUpdate NO tiene extra="forbid": campos desconocidos/id/
  tenant_id/equipment_id en PATCH se ignoran en silencio (200).
- No hay transiciones de status: cualquier string se acepta.
- GET /{id}/refacciones y fotos: solo existen POST fotos (sin GET).
- Falla.diagnosis_id se almacena pero ningun endpoint lo lee.
"""

import os
import uuid

import pytest
from fastapi.exceptions import ResponseValidationError
from sqlalchemy import select

import app.agents.falla_agent as falla_agent_module
import app.agents.reporte_agent as reporte_agent_module
import app.modules.diagnosis.agent as diagnosis_agent_module
from app.database import async_session
from app.models.base import TenantModel
from app.models.falla import Falla, FallaFoto
from app.modules.diagnosis.models import Report

from conftest import tenant_headers

pytestmark = pytest.mark.anyio

FALLA_RESPONSE_KEYS = {
    "id",
    "tenant_id",
    "equipment_id",
    "diagnosis_id",
    "parte",
    "pieza",
    "descripcion",
    "causa_raiz",
    "prioridad",
    "status",
    "notas",
    "created_at",
    "fotos",
}


@pytest.fixture
async def tenant_b(test_db):
    async with async_session() as session:
        tenant = TenantModel(name="Tenant B", slug=f"fb-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        await session.commit()
        data = {"tenant_id": tenant.id}
    yield data


async def create_falla(client, headers, equipment_id, **overrides):
    payload = {
        "equipment_id": str(equipment_id),
        "parte": "Motor",
        "pieza": "Inyector",
        "descripcion": "falla de prueba",
    }
    payload.update(overrides)
    return await client.post("/api/fallas/", json=payload, headers=headers)


# 1. Crear falla -----------------------------------------------------------------
async def test_create_falla_valid(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_falla(client, headers, test_db["equipment_id"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == FALLA_RESPONSE_KEYS
    assert body["tenant_id"] == str(test_db["tenant_id"])
    assert body["equipment_id"] == str(test_db["equipment_id"])
    assert body["diagnosis_id"] is None
    assert body["status"] == "detectada"
    assert body["prioridad"] == "normal"
    assert body["fotos"] == []

    async with async_session() as session:
        result = await session.execute(
            select(Falla).where(Falla.id == uuid.UUID(body["id"]))
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.tenant_id == test_db["tenant_id"]


async def test_create_falla_without_tenant_returns_400(client, test_db):
    res = await create_falla(client, {}, test_db["equipment_id"])
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


async def test_create_falla_unknown_equipment_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_falla(client, headers, uuid.uuid4())
    assert res.status_code == 404
    assert res.json()["detail"] == "Equipment not found"


async def test_create_falla_invalid_returns_422(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/fallas/",
        json={"equipment_id": str(test_db["equipment_id"]), "parte": "Motor"},
        headers=headers,
    )
    assert res.status_code == 422


async def test_create_falla_with_diagnosis_id_persisted(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    async with async_session() as session:
        session.add(
            Report(
                tenant_id=test_db["tenant_id"],
                equipment_id=str(test_db["equipment_id"]),
                title="Diagnostico previo",
                report_type="diagnosis",
                status="completed",
            )
        )
        await session.commit()
        result = await session.execute(select(Report))
        report_id = str(result.scalars().first().id)

    res = await create_falla(
        client, headers, test_db["equipment_id"], diagnosis_id=report_id
    )
    assert res.status_code == 200
    assert res.json()["diagnosis_id"] == report_id


# 2. Listar fallas ------------------------------------------------------------------
async def test_list_fallas_isolated_and_ordered(client, test_db, tenant_b):
    headers_a = tenant_headers(test_db["tenant_id"])
    first = await create_falla(client, headers_a, test_db["equipment_id"], pieza="A1")
    second = await create_falla(client, headers_a, test_db["equipment_id"], pieza="A2")
    assert first.status_code == 200 and second.status_code == 200

    res = await client.get("/api/fallas/", headers=headers_a)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    assert set(items[0].keys()) == FALLA_RESPONSE_KEYS
    assert [i["id"] for i in items] == [second.json()["id"], first.json()["id"]]
    assert all(i["tenant_id"] == str(test_db["tenant_id"]) for i in items)

    res_b = await client.get("/api/fallas/", headers=tenant_headers(tenant_b["tenant_id"]))
    assert res_b.status_code == 200
    assert res_b.json() == []


async def test_list_fallas_without_tenant_returns_400(client, test_db):
    res = await client.get("/api/fallas/")
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


async def test_list_fallas_filter_by_equipment(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    async with async_session() as session:
        from app.modules.equipment.models import Equipment

        session.add(
            Equipment(
                tenant_id=test_db["tenant_id"],
                brand="CAT",
                model="330D",
                serial_number=f"SN-F-{uuid.uuid4().hex[:8]}",
                equipment_type="loader",
            )
        )
        await session.commit()
        result = await session.execute(select(Equipment))
        eq_ids = [str(e.id) for e in result.scalars().all()]

    await create_falla(client, headers, eq_ids[0], pieza="P1")
    await create_falla(client, headers, eq_ids[1], pieza="P2")

    res = await client.get(
        "/api/fallas/", params={"equipment_id": eq_ids[0]}, headers=headers
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["equipment_id"] == eq_ids[0]

    res_empty = await client.get(
        "/api/fallas/", params={"equipment_id": str(uuid.uuid4())}, headers=headers
    )
    assert res_empty.status_code == 200
    assert res_empty.json() == []


# 3. Obtener falla ---------------------------------------------------------------------
async def test_get_own_falla(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    res = await client.get(f"/api/fallas/{created.json()['id']}", headers=headers)
    assert res.status_code == 200
    assert set(res.json().keys()) == FALLA_RESPONSE_KEYS


async def test_get_unknown_falla_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(f"/api/fallas/{uuid.uuid4()}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


async def test_get_falla_without_tenant_returns_404(client, test_db):
    # Comportamiento real: sin check 400 (404, no 400).
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    res = await client.get(f"/api/fallas/{created.json()['id']}")
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


# 4. PATCH falla ----------------------------------------------------------------------------
# CONTRATO CRITICO CONGELADO: PATCH escribe en DB pero la respuesta falla
# (update_falla no precarga `fotos` y FallaResponse la exige -> en prod:
# HTTP 500 "Internal Server Error"). Verificado en servidor local real.
# En tests ASGI la falla de serializacion emerge como ResponseValidationError.
async def test_patch_falla_status_persists_despite_500(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    fid = created.json()["id"]

    with pytest.raises(ResponseValidationError):
        await client.patch(
            f"/api/fallas/{fid}", json={"status": "en_reparacion"}, headers=headers
        )

    body = (await client.get(f"/api/fallas/{fid}", headers=headers)).json()
    assert body["status"] == "en_reparacion"
    assert body["parte"] == "Motor"
    assert body["pieza"] == "Inyector"
    assert body["equipment_id"] == str(test_db["equipment_id"])


async def test_patch_falla_partial_preserves_others_despite_500(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    fid = created.json()["id"]

    with pytest.raises(ResponseValidationError):
        await client.patch(
            f"/api/fallas/{fid}",
            json={"descripcion": "nueva descripcion", "prioridad": "urgente"},
            headers=headers,
        )

    body = (await client.get(f"/api/fallas/{fid}", headers=headers)).json()
    assert body["descripcion"] == "nueva descripcion"
    assert body["prioridad"] == "urgente"
    assert body["parte"] == "Motor"
    assert body["status"] == "detectada"


async def test_patch_falla_forbidden_and_unknown_fields_ignored(client, test_db):
    # FallaUpdate sin extra="forbid": 200/500 por serializacion, pero los
    # campos id/tenant_id/equipment_id/desconocidos jamas se escriben.
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    fid = created.json()["id"]
    before = created.json()

    with pytest.raises(ResponseValidationError):
        await client.patch(
            f"/api/fallas/{fid}",
            json={
                "equipment_id": str(uuid.uuid4()),
                "tenant_id": str(uuid.uuid4()),
                "id": str(uuid.uuid4()),
                "campo_desconocido": "x",
            },
            headers=headers,
        )

    after = (await client.get(f"/api/fallas/{fid}", headers=headers)).json()
    assert after["id"] == before["id"]
    assert after["tenant_id"] == before["tenant_id"]
    assert after["equipment_id"] == before["equipment_id"]


async def test_patch_falla_without_tenant_returns_404(client, test_db):
    # Comportamiento real: sin check 400 (404, no 400).
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    res = await client.patch(
        f"/api/fallas/{created.json()['id']}", json={"status": "x"}
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


async def test_patch_unknown_falla_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.patch(
        f"/api/fallas/{uuid.uuid4()}", json={"status": "x"}, headers=headers
    )
    assert res.status_code == 404


# 5. Tenant isolation ----------------------------------------------------------------------------
async def test_tenant_b_cannot_touch_tenant_a_falla(client, test_db, tenant_b):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])
    created = await create_falla(client, headers_a, test_db["equipment_id"])
    fid = created.json()["id"]

    assert (await client.get(f"/api/fallas/{fid}", headers=headers_b)).status_code == 404

    res_patch = await client.patch(
        f"/api/fallas/{fid}", json={"status": "HACK"}, headers=headers_b
    )
    assert res_patch.status_code == 404

    after = await client.get(f"/api/fallas/{fid}", headers=headers_a)
    assert after.status_code == 200
    assert after.json()["status"] == "detectada"


# 7. Estructurar falla con IA (mockeada) --------------------------------------------------------------
def patch_falla_agent(monkeypatch, final_state):
    class StubAgent:
        def __init__(self, state):
            self.state = state
            self.calls = []

        async def ainvoke(self, payload, config=None):
            self.calls.append({"input": payload, "config": config})
            return self.state

    stub = StubAgent(final_state)
    monkeypatch.setattr(falla_agent_module, "falla_agent", stub)
    return stub


async def test_estructurar_falla_valid(client, test_db, monkeypatch):
    stub = patch_falla_agent(monkeypatch, {
        "necesita_mas_info": False,
        "pregunta_seguimiento": "",
        "falla_estructurada": {
            "parte": "Motor", "pieza": "Bomba", "descripcion": "fuga",
            "causa_raiz": "sello", "prioridad": "urgente", "severidad": "moderado",
        },
    })
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/estructurar-falla",
        json={
            "equipment_id": str(test_db["equipment_id"]),
            "diagnostico_ia": "fuga de aceite",
            "descripcion_mecanico": "goteo visible",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == {
        "necesita_mas_info", "pregunta_seguimiento", "falla_estructurada",
    }
    assert body["necesita_mas_info"] is False
    assert body["falla_estructurada"]["pieza"] == "Bomba"
    assert len(stub.calls) == 1
    agent_input = stub.calls[0]["input"]
    assert agent_input["diagnostico_ia"] == "fuga de aceite"
    assert agent_input["marca"] == "CAT"
    assert agent_input["modelo"] == "320D"
    assert agent_input["horas"] == 1250.0


async def test_estructurar_falla_needs_more_info(client, test_db, monkeypatch):
    patch_falla_agent(monkeypatch, {
        "necesita_mas_info": True,
        "pregunta_seguimiento": "¿En qué parte ocurre?",
        "falla_estructurada": {},
    })
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/estructurar-falla",
        json={
            "equipment_id": str(test_db["equipment_id"]),
            "diagnostico_ia": "ruido",
            "descripcion_mecanico": "suena raro",
        },
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["necesita_mas_info"] is True
    assert body["pregunta_seguimiento"] == "¿En qué parte ocurre?"


async def test_estructurar_falla_without_tenant_returns_400(client, test_db, monkeypatch):
    stub = patch_falla_agent(monkeypatch, {"necesita_mas_info": False})
    res = await client.post(
        "/api/ai/estructurar-falla",
        json={
            "equipment_id": str(test_db["equipment_id"]),
            "diagnostico_ia": "x",
            "descripcion_mecanico": "y",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"
    assert stub.calls == []


async def test_estructurar_falla_unknown_equipment_returns_404(client, test_db, monkeypatch):
    stub = patch_falla_agent(monkeypatch, {"necesita_mas_info": False})
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/estructurar-falla",
        json={
            "equipment_id": str(uuid.uuid4()),
            "diagnostico_ia": "x",
            "descripcion_mecanico": "y",
        },
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Equipment not found"
    assert stub.calls == []


# 8. Fotos (solo POST existe) ------------------------------------------------------------------------------
async def test_upload_falla_foto(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    fid = created.json()["id"]

    res = await client.post(
        f"/api/fallas/{fid}/fotos",
        files={"file": ("foto.png", b"\x89PNG-fake-bytes", "image/png")},
        data={"descripcion": "evidencia lateral"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == {"id", "filename", "message"}
    assert body["message"] == "Foto subida"
    assert body["filename"].endswith(".png")

    async with async_session() as session:
        result = await session.execute(
            select(FallaFoto).where(FallaFoto.id == uuid.UUID(body["id"]))
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.tenant_id == test_db["tenant_id"]
    assert row.falla_id == uuid.UUID(fid)
    assert row.filename == body["filename"]
    # Comportamiento real: `descripcion` viaja en el form multipart pero el
    # endpoint la declara como query param -> se pierde (None). Congelado.
    assert row.descripcion is None
    assert os.path.exists(row.filepath)
    os.remove(row.filepath)


async def test_upload_falla_foto_unknown_falla_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        f"/api/fallas/{uuid.uuid4()}/fotos",
        files={"file": ("foto.png", b"bytes", "image/png")},
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


async def test_upload_falla_foto_without_tenant_returns_400(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    res = await client.post(
        f"/api/fallas/{created.json()['id']}/fotos",
        files={"file": ("foto.png", b"bytes", "image/png")},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


# 9. Integración con Parts (módulo ya extraído) ---------------------------------------------------------------
async def test_falla_parts_integration(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(client, headers, test_db["equipment_id"])
    fid = created.json()["id"]

    listed = await client.get(f"/api/fallas/{fid}/refacciones", headers=headers)
    assert listed.status_code == 200 and listed.json() == []

    created_ref = await client.post(
        f"/api/fallas/{fid}/refacciones",
        json={"nombre": "Filtro", "cantidad": 1},
        headers=headers,
    )
    assert created_ref.status_code == 200

    confirmed = await client.post(
        "/api/ai/confirmar-refacciones",
        json={"falla_id": fid, "refacciones": [{"nombre": "Banda"}]},
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["count"] == 1

    assert len((await client.get(
        f"/api/fallas/{fid}/refacciones", headers=headers)).json()) == 2


# 10. Consumidores cruzados ------------------------------------------------------------------------------------
class StubAgent:
    def __init__(self, final_state):
        self.final_state = final_state
        self.calls = []

    async def ainvoke(self, payload, config=None):
        self.calls.append({"input": payload, "config": config})
        return self.final_state


async def test_consumers_use_falla(client, test_db, monkeypatch):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_falla(
        client, headers, test_db["equipment_id"], parte="Hidráulico", pieza="Bomba"
    )
    fid = created.json()["id"]

    # Quotations
    cot = await client.post(
        "/api/cotizaciones/",
        json={"falla_id": fid, "subtotal_refacciones": 500.0, "mano_de_obra": 100.0},
        headers=headers,
    )
    assert cot.status_code == 200
    assert cot.json()["falla_id"] == fid
    pdf = await client.get(f"/api/cotizaciones/{cot.json()['id']}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content[:5] == b"%PDF-"

    # Repairs
    proc = await client.post(
        "/api/reparaciones/",
        json={"equipment_id": str(test_db["equipment_id"]), "falla_id": fid},
        headers=headers,
    )
    assert proc.status_code == 200
    assert proc.json()["falla_id"] == fid
    assert proc.json()["equipment_id"] == str(test_db["equipment_id"])

    # Reports (agente stub)
    stub_rep = StubAgent({
        "resumen_ejecutivo": "ok", "diagnostico": "d", "trabajo_realizado": "t",
        "refacciones_utilizadas": "r", "recomendaciones": "rec", "garantia": "g",
    })
    monkeypatch.setattr(reporte_agent_module, "reporte_agent", stub_rep)
    rep = await client.post(f"/api/reportes/generar/{fid}", headers=headers)
    assert rep.status_code == 200, rep.text
    assert rep.json()["falla_id"] == fid

    # Parts
    ref = await client.post(
        f"/api/fallas/{fid}/refacciones", json={"nombre": "Sello"}, headers=headers
    )
    assert ref.status_code == 200
    assert ref.json()["falla_id"] == fid

    # Equipment + Diagnosis (agente stub)
    eq = await client.get(
        f"/api/equipment/{test_db['equipment_id']}", headers=headers
    )
    assert eq.status_code == 200
    stub_diag = StubAgent({
        "symptoms": "x", "diagnosis": "y", "recommendations": [],
        "parts_needed": [], "estimated_hours": 1.0, "problem_type": "motor",
        "severity": "low", "necesita_mas_info": False,
    })
    monkeypatch.setattr(diagnosis_agent_module, "diagnosis_agent", stub_diag)
    diag = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "x"},
        headers=headers,
    )
    assert diag.status_code == 200

    # PATCH status persiste aunque la respuesta falle (contrato 500 congelado)
    with pytest.raises(ResponseValidationError):
        await client.patch(
            f"/api/fallas/{fid}", json={"status": "en_reparacion"}, headers=headers
        )
    assert (await client.get(f"/api/fallas/{fid}", headers=headers)).json()["status"] == "en_reparacion"
    assert (await client.get(
        f"/api/cotizaciones/{cot.json()['id']}", headers=headers)).status_code == 200
