"""ETAPA 0 (Equipment) — Tests de contrato y regresion del dominio Equipment.

Congela el comportamiento ACTUAL de /api/equipment/* y sus contratos
cruzados, SIN cambiar codigo productivo.

Hallazgos congelados aqui (deuda documentada, NO corregida):
- POST /equipment/ NO verifica serial duplicado (lo permite).
- GET /equipment/{id} SIN header de tenant responde 404 (no 400).
- El guard de DELETE cuenta fallas/reparaciones SIN filtrar por tenant.
- La unicidad de serial en PATCH esta acotada al tenant (duplicado
  cross-tenant permitido).
"""

import uuid

import pytest
from sqlalchemy import select

import app.agents.reporte_agent as reporte_agent_module
import app.modules.diagnosis.agent as diagnosis_agent_module
from app.database import async_session
from app.models.base import TenantModel
from app.modules.equipment.models import Equipment
from app.models.falla import Falla, ProcedimientoReparacion

from conftest import tenant_headers

pytestmark = pytest.mark.anyio

EQUIPMENT_RESPONSE_KEYS = {
    "id",
    "tenant_id",
    "brand",
    "model",
    "serial_number",
    "equipment_type",
    "hours",
    "year",
    "client_id",
    "notes",
    "created_at",
}


def new_serial(prefix="SN"):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture
async def tenant_b(test_db):
    """Segundo tenant con su propio equipo. Limpieza via test_db teardown."""
    async with async_session() as session:
        tenant = TenantModel(name="Tenant B", slug=f"b-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        equipment = Equipment(
            tenant_id=tenant.id,
            brand="Komatsu",
            model="PC200",
            serial_number=new_serial("SN-B"),
            equipment_type="excavator",
            hours=500.0,
            year=2021,
            client_id=None,
            notes=None,
        )
        session.add(equipment)
        await session.flush()
        await session.commit()
        data = {"tenant_id": tenant.id, "equipment_id": equipment.id,
                "serial_number": equipment.serial_number}
    yield data


async def create_equipment(client, headers, serial=None, **overrides):
    payload = {
        "brand": "CAT",
        "model": "320D",
        "serial_number": serial or new_serial(),
        "equipment_type": "excavator",
    }
    payload.update(overrides)
    res = await client.post("/api/equipment/", json=payload, headers=headers)
    return res


# 1. Create equipment ----------------------------------------------------------
async def test_create_equipment_valid(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_equipment(
        client, headers, hours=100.0, year=2020, notes="nota inicial"
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == EQUIPMENT_RESPONSE_KEYS
    assert body["tenant_id"] == str(test_db["tenant_id"])
    assert body["brand"] == "CAT"
    assert body["hours"] == 100.0
    assert body["year"] == 2020

    async with async_session() as session:
        result = await session.execute(
            select(Equipment).where(Equipment.id == uuid.UUID(body["id"]))
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.tenant_id == test_db["tenant_id"]
    assert row.serial_number == body["serial_number"]


async def test_create_equipment_without_tenant_returns_400(client, test_db):
    res = await create_equipment(client, {}, serial=new_serial())
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "320D", "serial_number": "X", "equipment_type": "excavator"},
        {"brand": "CAT", "model": "320D", "serial_number": "X", "equipment_type": "excavator", "hours": -5},
        {"brand": "CAT", "model": "320D", "serial_number": "X", "equipment_type": "excavator", "year": 1800},
    ],
)
async def test_create_equipment_invalid_returns_422(client, test_db, payload):
    headers = tenant_headers(test_db["tenant_id"])
    if "serial_number" in payload and payload["serial_number"] == "X":
        payload = dict(payload, serial_number=new_serial())
    res = await client.post("/api/equipment/", json=payload, headers=headers)
    assert res.status_code == 422


# 2. List equipment: aislamiento por tenant -------------------------------------
async def test_list_equipment_isolated_by_tenant(client, test_db, tenant_b):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])

    res_a = await client.get("/api/equipment/", headers=headers_a)
    res_b = await client.get("/api/equipment/", headers=headers_b)
    assert res_a.status_code == 200
    assert res_b.status_code == 200

    ids_a = {e["id"] for e in res_a.json()}
    ids_b = {e["id"] for e in res_b.json()}
    assert str(test_db["equipment_id"]) in ids_a
    assert str(tenant_b["equipment_id"]) not in ids_a
    assert str(tenant_b["equipment_id"]) in ids_b
    assert str(test_db["equipment_id"]) not in ids_b
    assert all(e["tenant_id"] == str(test_db["tenant_id"]) for e in res_a.json())
    assert all(e["tenant_id"] == str(tenant_b["tenant_id"]) for e in res_b.json())


async def test_list_equipment_without_tenant_returns_400(client, test_db):
    res = await client.get("/api/equipment/")
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


# 3. Get equipment ----------------------------------------------------------------
async def test_get_own_equipment(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(f"/api/equipment/{test_db['equipment_id']}", headers=headers)
    assert res.status_code == 200
    assert set(res.json().keys()) == EQUIPMENT_RESPONSE_KEYS
    assert res.json()["id"] == str(test_db["equipment_id"])


async def test_get_unknown_equipment_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(f"/api/equipment/{uuid.uuid4()}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Equipment not found"


async def test_get_equipment_without_tenant_returns_404(client, test_db):
    # Comportamiento real: get_equipment NO valida tenant (404, no 400).
    res = await client.get(f"/api/equipment/{test_db['equipment_id']}")
    assert res.status_code == 404
    assert res.json()["detail"] == "Equipment not found"


# 4. PATCH parcial por campo + exclude_unset ------------------------------------------
@pytest.mark.parametrize(
    "field,value",
    [
        ("brand", "John Deere"),
        ("model", "330D"),
        ("serial_number", "SN-PATCHED-001"),
        ("equipment_type", "loader"),
        ("hours", 1300.5),
        ("year", 2020),
        ("notes", "nota actualizada"),
    ],
)
async def test_patch_single_field_preserves_others(client, test_db, field, value):
    headers = tenant_headers(test_db["tenant_id"])
    eq_id = str(test_db["equipment_id"])
    serial = new_serial("SN-P")
    if field == "serial_number":
        value = serial

    before = (await client.get(f"/api/equipment/{eq_id}", headers=headers)).json()
    res = await client.patch(f"/api/equipment/{eq_id}", json={field: value}, headers=headers)
    assert res.status_code == 200, res.text
    after = res.json()
    assert after[field] == value
    for key in EQUIPMENT_RESPONSE_KEYS - {"id", "tenant_id", "created_at", field, "client_id"}:
        assert after[key] == before[key], f"campo no enviado modificado: {key}"


async def test_patch_invalid_value_returns_422(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.patch(
        f"/api/equipment/{test_db['equipment_id']}",
        json={"hours": -1},
        headers=headers,
    )
    assert res.status_code == 422


async def test_patch_without_tenant_returns_400(client, test_db):
    res = await client.patch(
        f"/api/equipment/{test_db['equipment_id']}", json={"brand": "X"}
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


# 5. Campos prohibidos en PATCH ------------------------------------------------------------
@pytest.mark.parametrize(
    "payload",
    [
        {"client_id": str(uuid.uuid4())},
        {"tenant_id": str(uuid.uuid4())},
        {"campo_desconocido": "x"},
    ],
)
async def test_patch_forbidden_fields_returns_422(client, test_db, payload):
    headers = tenant_headers(test_db["tenant_id"])
    eq_id = str(test_db["equipment_id"])
    before = (await client.get(f"/api/equipment/{eq_id}", headers=headers)).json()
    res = await client.patch(f"/api/equipment/{eq_id}", json=payload, headers=headers)
    assert res.status_code == 422
    after = (await client.get(f"/api/equipment/{eq_id}", headers=headers)).json()
    assert after == before


# 6. Identidad: id / tenant_id / client_id nunca cambian ---------------------------------------
async def test_patch_never_changes_identity(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    client_id = str(uuid.uuid4())
    created = await create_equipment(client, headers, client_id=client_id)
    assert created.status_code == 200
    eq_id = created.json()["id"]

    res = await client.patch(f"/api/equipment/{eq_id}", json={"brand": "CAT-NEW"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == eq_id
    assert body["tenant_id"] == str(test_db["tenant_id"])
    assert body["client_id"] == client_id


# 7. Serial duplicado ---------------------------------------------------------------------------
async def test_create_duplicate_serial_same_tenant_allowed(client, test_db):
    # Comportamiento real: POST NO verifica unicidad (deuda documentada).
    headers = tenant_headers(test_db["tenant_id"])
    serial = new_serial("SN-DUP")
    first = await create_equipment(client, headers, serial=serial)
    second = await create_equipment(client, headers, serial=serial)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]

    async with async_session() as session:
        result = await session.execute(
            select(Equipment).where(
                Equipment.serial_number == serial,
                Equipment.tenant_id == test_db["tenant_id"],
            )
        )
        assert len(result.scalars().all()) == 2


async def test_patch_duplicate_serial_same_tenant_returns_409(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_equipment(client, headers)
    assert created.status_code == 200
    other_id = created.json()["id"]

    before = (await client.get(f"/api/equipment/{other_id}", headers=headers)).json()
    res = await client.patch(
        f"/api/equipment/{other_id}",
        json={"serial_number": "SN-TEST-001"},
        headers=headers,
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Serial number already exists"
    after = (await client.get(f"/api/equipment/{other_id}", headers=headers)).json()
    assert after == before


async def test_patch_same_serial_value_is_allowed(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.patch(
        f"/api/equipment/{test_db['equipment_id']}",
        json={"serial_number": "SN-TEST-001"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["serial_number"] == "SN-TEST-001"


async def test_patch_duplicate_serial_cross_tenant_allowed(client, test_db, tenant_b):
    # Comportamiento real: el check esta acotado al tenant (deuda documentada).
    headers_b = tenant_headers(tenant_b["tenant_id"])
    res = await client.patch(
        f"/api/equipment/{tenant_b['equipment_id']}",
        json={"serial_number": "SN-TEST-001"},
        headers=headers_b,
    )
    assert res.status_code == 200
    assert res.json()["serial_number"] == "SN-TEST-001"


# 8. DELETE sin historial ------------------------------------------------------------------------------
async def test_delete_equipment_without_history(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_equipment(client, headers)
    eq_id = created.json()["id"]

    res = await client.delete(f"/api/equipment/{eq_id}", headers=headers)
    assert res.status_code == 200
    assert res.json() == {"message": "Equipo eliminado"}

    gone = await client.get(f"/api/equipment/{eq_id}", headers=headers)
    assert gone.status_code == 404


async def test_delete_without_tenant_returns_400(client, test_db):
    res = await client.delete(f"/api/equipment/{test_db['equipment_id']}")
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


# 9. DELETE con historial (guard) ---------------------------------------------------------------------------
async def _create_falla(client, headers, equipment_id):
    res = await client.post(
        "/api/fallas/",
        json={
            "equipment_id": str(equipment_id),
            "parte": "Motor",
            "pieza": "Inyector",
            "descripcion": "falla de prueba",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def _create_procedimiento(client, headers, equipment_id, falla_id=None):
    payload = {"equipment_id": str(equipment_id)}
    if falla_id:
        payload["falla_id"] = str(falla_id)
    res = await client.post("/api/reparaciones/", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


async def test_delete_equipment_with_falla_returns_409(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_equipment(client, headers)
    eq_id = created.json()["id"]
    falla = await _create_falla(client, headers, eq_id)

    res = await client.delete(f"/api/equipment/{eq_id}", headers=headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "El sistema no permite eliminar maquinas con historial"

    assert (await client.get(f"/api/equipment/{eq_id}", headers=headers)).status_code == 200
    assert (await client.get(f"/api/fallas/{falla['id']}", headers=headers)).status_code == 200


async def test_delete_equipment_with_procedimiento_returns_409(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_equipment(client, headers)
    eq_id = created.json()["id"]
    proc = await _create_procedimiento(client, headers, eq_id)

    res = await client.delete(f"/api/equipment/{eq_id}", headers=headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "El sistema no permite eliminar maquinas con historial"

    assert (await client.get(f"/api/equipment/{eq_id}", headers=headers)).status_code == 200
    assert (await client.get(f"/api/reparaciones/{proc['id']}", headers=headers)).status_code == 200


# 10. Tenant isolation en escritura ------------------------------------------------------------------------------
async def test_tenant_b_cannot_touch_tenant_a_equipment(client, test_db, tenant_b):
    headers_b = tenant_headers(tenant_b["tenant_id"])
    headers_a = tenant_headers(test_db["tenant_id"])
    eq_id = str(test_db["equipment_id"])

    assert (await client.get(f"/api/equipment/{eq_id}", headers=headers_b)).status_code == 404

    res_patch = await client.patch(
        f"/api/equipment/{eq_id}", json={"brand": "HACK"}, headers=headers_b
    )
    assert res_patch.status_code == 404
    assert res_patch.json()["detail"] == "Equipment not found"

    res_delete = await client.delete(f"/api/equipment/{eq_id}", headers=headers_b)
    assert res_delete.status_code == 404

    after = await client.get(f"/api/equipment/{eq_id}", headers=headers_a)
    assert after.status_code == 200
    assert after.json()["brand"] == "CAT"


# 11. Relaciones preservadas tras update ----------------------------------------------------------------------------
async def test_relations_preserved_after_equipment_update(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_equipment(client, headers)
    eq_id = created.json()["id"]
    falla = await _create_falla(client, headers, eq_id)
    proc = await _create_procedimiento(client, headers, eq_id, falla["id"])

    res = await client.patch(
        f"/api/equipment/{eq_id}",
        json={"brand": "CAT-UPD", "notes": "nueva nota"},
        headers=headers,
    )
    assert res.status_code == 200

    falla_after = (await client.get(f"/api/fallas/{falla['id']}", headers=headers)).json()
    proc_after = (await client.get(f"/api/reparaciones/{proc['id']}", headers=headers)).json()
    assert falla_after["equipment_id"] == eq_id
    assert proc_after["equipment_id"] == eq_id
    assert proc_after["falla_id"] == falla["id"]


# 12. Consumidores: leen Equipment tras operaciones normales -----------------------------------------
class StubAgent:
    def __init__(self, final_state):
        self.final_state = final_state
        self.calls = []

    async def ainvoke(self, payload, config=None):
        self.calls.append({"input": payload, "config": config})
        return self.final_state


async def test_consumers_read_equipment_after_update(client, test_db, monkeypatch):
    headers = tenant_headers(test_db["tenant_id"])
    created = await create_equipment(client, headers, hours=200.0)
    eq_id = created.json()["id"]

    # Update + falla + refaccion + cotizacion + PDF (Quotations/Parts/Failures)
    assert (await client.patch(
        f"/api/equipment/{eq_id}", json={"hours": 250.0, "notes": "post-update"}, headers=headers
    )).status_code == 200
    falla = await _create_falla(client, headers, eq_id)

    ref = await client.post(
        f"/api/fallas/{falla['id']}/refacciones",
        json={"nombre": "Filtro", "cantidad": 1},
        headers=headers,
    )
    assert ref.status_code == 200

    cot = await client.post(
        "/api/cotizaciones/",
        json={"falla_id": falla["id"], "subtotal_refacciones": 100.0, "mano_de_obra": 50.0},
        headers=headers,
    )
    assert cot.status_code == 200

    pdf = await client.get(f"/api/cotizaciones/{cot.json()['id']}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-"

    # Repairs: procedimiento verifica equipment + falla
    proc = await _create_procedimiento(client, headers, eq_id, falla["id"])
    assert proc["equipment_id"] == eq_id

    # Reports: generar usa Falla + Equipment + Refaccion + Procedimiento (agente stub)
    stub_rep = StubAgent({
        "contenido": {
            "resumen_ejecutivo": "ok",
            "diagnostico": "d",
            "trabajo_realizado": "t",
            "refacciones_utilizadas": "r",
            "recomendaciones": "rec",
            "garantia": "g",
        }
    })
    monkeypatch.setattr(reporte_agent_module, "reporte_agent", stub_rep)
    rep = await client.post(f"/api/reportes/generar/{falla['id']}", headers=headers)
    assert rep.status_code == 200, rep.text
    assert set(rep.json().keys()) == {"id", "falla_id", "contenido", "pdf_url", "fecha_generacion"}

    rpdf = await client.get(f"/api/reportes/{rep.json()['id']}/pdf", headers=headers)
    assert rpdf.status_code == 200
    assert rpdf.headers["content-type"] == "application/pdf"
    assert rpdf.content[:5] == b"%PDF-"

    # Equipment sigue legible y con los valores actualizados
    eq_after = (await client.get(f"/api/equipment/{eq_id}", headers=headers)).json()
    assert eq_after["hours"] == 250.0
    assert eq_after["notes"] == "post-update"


async def test_diagnosis_reads_equipment(client, test_db, monkeypatch):
    stub = StubAgent({
        "symptoms": "humo",
        "diagnosis": "inyectores",
        "recommendations": [],
        "parts_needed": [],
        "estimated_hours": 1.0,
        "problem_type": "motor",
        "severity": "low",
        "necesita_mas_info": False,
    })
    monkeypatch.setattr(diagnosis_agent_module, "diagnosis_agent", stub)
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "humo"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["diagnosis"] == "inyectores"
