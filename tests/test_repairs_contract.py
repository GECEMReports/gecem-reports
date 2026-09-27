"""ETAPA 0 (Repairs) — Tests de contrato y regresion del dominio Reparaciones.

Congela el comportamiento ACTUAL de:
- POST/GET /api/reparaciones/, GET /{id}, POST /{id}/pasos,
  POST /{id}/pasos/{paso}/fotos, PATCH /{id}/completar
SIN cambiar codigo productivo. Sin LLM (este dominio no usa agentes).

Hallazgos congelados aqui (deuda documentada, NO corregida):
- GET /{id} y PATCH completar SIN tenant responden 404 (sin check 400).
- `uuid.UUID()` sin validar: equipment_id/falla_id/cotizacion_id
  malformados propagan ValueError (500 en prod).
- cotizacion_id inexistente pero bien formado -> lo rechaza la FK de DB.
- numeracion de pasos = len(existentes)+1 (sin endpoint de borrado
  equivale a max+1, pero no hay proteccion contra huecos).
- PasoFoto NO tiene descripcion ni endpoint GET (solo POST + filepath).
- El modelo/DB permite N procedimientos por falla (sin unique);
  Reports asume <=1 y rompe con MultipleResultsFound (bug de Reports,
  reproducido aqui sin corregir).

Nota ETAPA 0.5 (hotfix aplicado): POST /pasos devolvia HTTP 500 porque
add_paso no precargaba `fotos`; ahora usa selectinload y responde 200.
Solo cambia la serializacion; numeracion, tenant y persistencia intactos.
"""

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound

import app.agents.reporte_agent as reporte_agent_module
from app.database import async_session
from app.models.base import TenantModel
from app.modules.repairs.models import PasoFoto, PasoReparacion, ProcedimientoReparacion
from app.modules.equipment.models import Equipment

from conftest import tenant_headers

pytestmark = pytest.mark.anyio

PROCEDIMIENTO_RESPONSE_KEYS = {
    "id",
    "equipment_id",
    "falla_id",
    "cotizacion_id",
    "mecanico_id",
    "descripcion",
    "tipo",
    "tiempo_total_horas",
    "notas",
    "status",
    "created_at",
    "pasos",
}

PASO_RESPONSE_KEYS = {
    "id",
    "procedimiento_id",
    "numero_paso",
    "descripcion",
    "tiempo_minutos",
    "fotos",
}

PASO_FOTO_RESPONSE_KEYS = {"id", "filename", "filepath"}


@pytest.fixture
async def tenant_b(test_db):
    async with async_session() as session:
        tenant = TenantModel(name="Tenant B", slug=f"rb-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        equipment = Equipment(
            tenant_id=tenant.id,
            brand="Komatsu",
            model="PC200",
            serial_number=f"SN-RB-{uuid.uuid4().hex[:8]}",
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
            "pieza": "Bomba",
            "descripcion": "falla para reparar",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def create_procedimiento(client, headers, equipment_id, **overrides):
    payload = {"equipment_id": str(equipment_id)}
    payload.update({k: str(v) if k in ("falla_id", "cotizacion_id") and v else v for k, v in overrides.items()})
    return await client.post("/api/reparaciones/", json=payload, headers=headers)


# 1. Crear procedimiento -----------------------------------------------------------
async def test_create_procedimiento_valid(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_procedimiento(
        client, headers, test_db["equipment_id"],
        falla_id=falla_a["id"], descripcion="reparación mayor",
        tipo="correctiva", notas="nota inicial",
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == PROCEDIMIENTO_RESPONSE_KEYS
    assert body["equipment_id"] == str(test_db["equipment_id"])
    assert body["falla_id"] == falla_a["id"]
    assert body["cotizacion_id"] is None
    assert body["mecanico_id"] is None
    assert body["descripcion"] == "reparación mayor"
    assert body["tipo"] == "correctiva"
    assert body["tiempo_total_horas"] == 0
    assert body["status"] == "en_progreso"
    assert body["pasos"] == []

    async with async_session() as session:
        result = await session.execute(
            select(ProcedimientoReparacion).where(
                ProcedimientoReparacion.id == uuid.UUID(body["id"])
            )
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.tenant_id == test_db["tenant_id"]


async def test_create_procedimiento_without_falla(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_procedimiento(client, headers, test_db["equipment_id"])
    assert res.status_code == 200
    assert res.json()["falla_id"] is None


async def test_create_procedimiento_with_cotizacion(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    cot = (
        await client.post(
            "/api/cotizaciones/",
            json={"falla_id": falla_a["id"], "mano_de_obra": 10},
            headers=headers,
        )
    ).json()
    res = await create_procedimiento(
        client, headers, test_db["equipment_id"],
        falla_id=falla_a["id"], cotizacion_id=cot["id"],
    )
    assert res.status_code == 200
    assert res.json()["cotizacion_id"] == cot["id"]


async def test_create_procedimiento_unknown_cotizacion_id_fails(client, test_db, falla_a):
    # Comportamiento real: sin verificacion previa; la FK de DB lo rechaza.
    headers = tenant_headers(test_db["tenant_id"])
    with pytest.raises(Exception):
        await create_procedimiento(
            client, headers, test_db["equipment_id"],
            falla_id=falla_a["id"], cotizacion_id=str(uuid.uuid4()),
        )


async def test_create_procedimiento_without_tenant_returns_400(client, test_db):
    res = await create_procedimiento(client, {}, test_db["equipment_id"])
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


async def test_create_procedimiento_unknown_equipment_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_procedimiento(client, headers, uuid.uuid4())
    assert res.status_code == 404
    assert res.json()["detail"] == "Equipment not found"


async def test_create_procedimiento_unknown_falla_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await create_procedimiento(
        client, headers, test_db["equipment_id"], falla_id=str(uuid.uuid4())
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Falla not found"


async def test_create_procedimiento_malformed_id_raises(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    with pytest.raises(ValueError):
        await create_procedimiento(client, headers, "no-es-uuid")


async def test_create_procedimiento_missing_equipment_returns_422(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post("/api/reparaciones/", json={}, headers=headers)
    assert res.status_code == 422


# 2. Listar procedimientos ----------------------------------------------------------------
async def test_list_procedimientos_isolated_filtered_ordered(client, test_db, tenant_b, falla_a):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])
    first = await create_procedimiento(client, headers_a, test_db["equipment_id"], falla_id=falla_a["id"])
    second = await create_procedimiento(client, headers_a, test_db["equipment_id"])
    other = await create_procedimiento(client, headers_b, tenant_b["equipment_id"])
    assert first.status_code == 200 and second.status_code == 200 and other.status_code == 200

    res = await client.get("/api/reparaciones/", headers=headers_a)
    assert res.status_code == 200
    items = res.json()
    assert [i["id"] for i in items] == [second.json()["id"], first.json()["id"]]
    assert set(items[0].keys()) == PROCEDIMIENTO_RESPONSE_KEYS

    assert (await client.get("/api/reparaciones/", headers=headers_b)).json()[0]["id"] == other.json()["id"]

    by_eq = await client.get(
        "/api/reparaciones/",
        params={"equipment_id": str(test_db["equipment_id"])},
        headers=headers_a,
    )
    assert len(by_eq.json()) == 2
    by_falla = await client.get(
        "/api/reparaciones/", params={"falla_id": falla_a["id"]}, headers=headers_a
    )
    assert [i["id"] for i in by_falla.json()] == [first.json()["id"]]


async def test_list_procedimientos_without_tenant_returns_400(client, test_db):
    res = await client.get("/api/reparaciones/")
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"


# 3. Obtener procedimiento ----------------------------------------------------------------------
async def test_get_own_procedimiento_with_pasos(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"], falla_id=falla_a["id"])
    await _add_paso(
        client, headers, proc.json()["id"],
        {"descripcion": "desarmar", "tiempo_minutos": 30},
    )

    res = await client.get(f"/api/reparaciones/{proc.json()['id']}", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == PROCEDIMIENTO_RESPONSE_KEYS
    assert len(body["pasos"]) == 1
    assert set(body["pasos"][0].keys()) == PASO_RESPONSE_KEYS
    assert body["pasos"][0]["descripcion"] == "desarmar"
    assert body["pasos"][0]["fotos"] == []


async def test_get_unknown_procedimiento_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.get(f"/api/reparaciones/{uuid.uuid4()}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Procedimiento not found"


async def test_get_procedimiento_without_tenant_returns_404(client, test_db, falla_a):
    # Comportamiento real: sin check 400 (404, no 400).
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    res = await client.get(f"/api/reparaciones/{proc.json()['id']}")
    assert res.status_code == 404


async def test_get_other_tenant_procedimiento_returns_404(client, test_db, tenant_b, falla_a):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])
    proc = await create_procedimiento(client, headers_a, test_db["equipment_id"])
    res = await client.get(f"/api/reparaciones/{proc.json()['id']}", headers=headers_b)
    assert res.status_code == 404


# 4. Agregar paso ----------------------------------------------------------------------------------------
# HOTFIX ETAPA 0.5: add_paso recarga el paso con `fotos` (selectinload) ->
# HTTP 200 con PasoResponse completo. Solo cambia la serializacion;
# numeracion, tenant y persistencia quedan intactas.
async def _add_paso(client, headers, pid, payload):
    res = await client.post(
        f"/api/reparaciones/{pid}/pasos", json=payload, headers=headers
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_add_pasos_numbered_sequentially(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    pid = proc.json()["id"]

    first = await _add_paso(
        client, headers, pid, {"descripcion": "paso uno", "tiempo_minutos": 15}
    )
    second = await _add_paso(client, headers, pid, {"descripcion": "paso dos"})
    assert first["numero_paso"] == 1
    assert second["numero_paso"] == 2
    assert set(first.keys()) == PASO_RESPONSE_KEYS
    assert first["procedimiento_id"] == pid
    assert first["descripcion"] == "paso uno"
    assert first["tiempo_minutos"] == 15
    assert first["fotos"] == []
    assert second["tiempo_minutos"] == 0

    persisted = (await client.get(f"/api/reparaciones/{pid}", headers=headers)).json()
    assert [p["numero_paso"] for p in persisted["pasos"]] == [1, 2]

    async with async_session() as session:
        result = await session.execute(
            select(PasoReparacion).where(PasoReparacion.procedimiento_id == uuid.UUID(pid))
        )
        assert len(result.scalars().all()) == 2


async def test_add_paso_serializes_fotos(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    pid = proc.json()["id"]
    paso = await _add_paso(client, headers, pid, {"descripcion": "revisar"})
    assert paso["fotos"] == []

    foto = await client.post(
        f"/api/reparaciones/{pid}/pasos/{paso['id']}/fotos",
        files={"file": ("p.png", b"\x89PNG-fake", "image/png")},
        headers=headers,
    )
    assert foto.status_code == 200

    body = (await client.get(f"/api/reparaciones/{pid}", headers=headers)).json()
    assert len(body["pasos"][0]["fotos"]) == 1
    assert set(body["pasos"][0]["fotos"][0].keys()) == PASO_FOTO_RESPONSE_KEYS
    assert body["pasos"][0]["fotos"][0]["filename"].endswith(".png")

    async with async_session() as session:
        for row in (
            await session.execute(select(PasoFoto))
        ).scalars().all():
            if os.path.exists(row.filepath):
                os.remove(row.filepath)


async def test_add_paso_unknown_procedimiento_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        f"/api/reparaciones/{uuid.uuid4()}/pasos",
        json={"descripcion": "x"},
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Procedimiento not found"


async def test_add_paso_without_tenant_returns_400(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    res = await client.post(
        f"/api/reparaciones/{proc.json()['id']}/pasos", json={"descripcion": "x"}
    )
    assert res.status_code == 400


async def test_add_paso_other_tenant_procedimiento_returns_404(client, test_db, tenant_b, falla_a):
    headers_a = tenant_headers(test_db["tenant_id"])
    headers_b = tenant_headers(tenant_b["tenant_id"])
    proc = await create_procedimiento(client, headers_a, test_db["equipment_id"])
    res = await client.post(
        f"/api/reparaciones/{proc.json()['id']}/pasos",
        json={"descripcion": "x"},
        headers=headers_b,
    )
    assert res.status_code == 404


# 5. Foto de paso (solo POST existe; sin GET) ---------------------------------------------------------------
async def test_upload_paso_foto(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    pid = proc.json()["id"]
    paso_id = (await _add_paso(client, headers, pid, {"descripcion": "revisar"}))["id"]

    res = await client.post(
        f"/api/reparaciones/{pid}/pasos/{paso_id}/fotos",
        files={"file": ("paso.png", b"\x89PNG-fake", "image/png")},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body.keys()) == PASO_FOTO_RESPONSE_KEYS
    assert body["filename"].endswith(".png")

    async with async_session() as session:
        result = await session.execute(
            select(PasoFoto).where(PasoFoto.id == uuid.UUID(body["id"]))
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.paso_id == uuid.UUID(paso_id)
    assert row.tenant_id == test_db["tenant_id"]
    assert os.path.exists(row.filepath)
    os.remove(row.filepath)


async def test_upload_paso_foto_unknown_paso_returns_404(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    res = await client.post(
        f"/api/reparaciones/{proc.json()['id']}/pasos/{uuid.uuid4()}/fotos",
        files={"file": ("p.png", b"x", "image/png")},
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Paso not found"


async def test_upload_paso_foto_without_tenant_returns_400(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    pid = proc.json()["id"]
    paso_id = (await _add_paso(client, headers, pid, {"descripcion": "x"}))["id"]
    res = await client.post(
        f"/api/reparaciones/{pid}/pasos/{paso_id}/fotos",
        files={"file": ("p.png", b"x", "image/png")},
    )
    assert res.status_code == 400


# 6. Completar procedimiento -----------------------------------------------------------------------------------
async def test_completar_procedimiento(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(
        client, headers, test_db["equipment_id"], falla_id=falla_a["id"]
    )
    pid = proc.json()["id"]

    res = await client.patch(
        f"/api/reparaciones/{pid}/completar",
        json={"tiempo_total_horas": 3.5, "notas": "trabajo terminado"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "completado"
    assert body["tiempo_total_horas"] == 3.5
    assert body["notas"] == "trabajo terminado"
    assert body["equipment_id"] == str(test_db["equipment_id"])
    assert body["falla_id"] == falla_a["id"]

    persisted = (await client.get(f"/api/reparaciones/{pid}", headers=headers)).json()
    assert persisted["status"] == "completado"


async def test_completar_procedimiento_twice_is_idempotent(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    pid = proc.json()["id"]
    payload = {"tiempo_total_horas": 1.0}
    first = await client.patch(f"/api/reparaciones/{pid}/completar", json=payload, headers=headers)
    second = await client.patch(f"/api/reparaciones/{pid}/completar", json=payload, headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert second.json()["status"] == "completado"


async def test_completar_unknown_procedimiento_returns_404(client, test_db):
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.patch(
        f"/api/reparaciones/{uuid.uuid4()}/completar",
        json={"tiempo_total_horas": 1.0},
        headers=headers,
    )
    assert res.status_code == 404


async def test_completar_without_tenant_returns_404(client, test_db, falla_a):
    # Comportamiento real: sin check 400 (404, no 400).
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(client, headers, test_db["equipment_id"])
    res = await client.patch(
        f"/api/reparaciones/{proc.json()['id']}/completar",
        json={"tiempo_total_horas": 1.0},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Procedimiento not found"


# 7. Relaciones ---------------------------------------------------------------------------------------------------
async def test_relations_preserved(client, test_db, falla_a):
    headers = tenant_headers(test_db["tenant_id"])
    cot = (
        await client.post(
            "/api/cotizaciones/",
            json={"falla_id": falla_a["id"], "mano_de_obra": 5},
            headers=headers,
        )
    ).json()
    proc = await create_procedimiento(
        client, headers, test_db["equipment_id"],
        falla_id=falla_a["id"], cotizacion_id=cot["id"],
    )
    await _add_paso(client, headers, proc.json()["id"], {"descripcion": "x"})
    paso_id = (
        await client.get(f"/api/reparaciones/{proc.json()['id']}", headers=headers)
    ).json()["pasos"][0]["id"]
    foto = await client.post(
        f"/api/reparaciones/{proc.json()['id']}/pasos/{paso_id}/fotos",
        files={"file": ("p.png", b"x", "image/png")},
        headers=headers,
    )
    assert foto.status_code == 200

    async with async_session() as session:
        proc_row = (
            await session.execute(
                select(ProcedimientoReparacion).where(
                    ProcedimientoReparacion.id == uuid.UUID(proc.json()["id"])
                )
            )
        ).scalar_one()
        assert proc_row.equipment_id == test_db["equipment_id"]
        assert proc_row.falla_id == uuid.UUID(falla_a["id"])
        assert proc_row.cotizacion_id == uuid.UUID(cot["id"])
        assert proc_row.tenant_id == test_db["tenant_id"]

        paso_row = (
            await session.execute(
                select(PasoReparacion).where(PasoReparacion.id == uuid.UUID(paso_id))
            )
        ).scalar_one()
        assert paso_row.procedimiento_id == proc_row.id

        foto_row = (
            await session.execute(
                select(PasoFoto).where(PasoFoto.id == uuid.UUID(foto.json()["id"]))
            )
        ).scalar_one()
        assert foto_row.paso_id == paso_row.id
        assert os.path.exists(foto_row.filepath)
        os.remove(foto_row.filepath)


# 9. Consumidor Reports + cardinalidad ------------------------------------------------------------------------------
class StubReporteAgent:
    def __init__(self, contenido):
        self.contenido = contenido

    async def ainvoke(self, payload, config=None):
        return {"contenido": self.contenido}


CONSUMER_CONTENIDO = {
    "resumen_ejecutivo": "ok", "diagnostico": "d", "trabajo_realizado": "t",
    "refacciones_utilizadas": "r", "recomendaciones": "rec", "garantia": "g",
}


async def test_reports_consumes_single_procedimiento(client, test_db, falla_a, monkeypatch):
    headers = tenant_headers(test_db["tenant_id"])
    proc = await create_procedimiento(
        client, headers, test_db["equipment_id"], falla_id=falla_a["id"]
    )
    assert proc.status_code == 200

    monkeypatch.setattr(
        "app.agents.reporte_agent.reporte_agent", StubReporteAgent(CONSUMER_CONTENIDO)
    )
    rep = await client.post(f"/api/reportes/generar/{falla_a['id']}", headers=headers)
    assert rep.status_code == 200, rep.text
    assert rep.json()["falla_id"] == falla_a["id"]


async def test_two_procedimientos_break_reports_generar(client, test_db, falla_a, monkeypatch):
    # HALLAZGO CRITICO (bug de Reports, NO corregir aqui): el modelo/DB
    # permite N procedimientos por falla, pero generar usa
    # scalar_one_or_none -> MultipleResultsFound con 2 procedimientos.
    headers = tenant_headers(test_db["tenant_id"])
    first = await create_procedimiento(
        client, headers, test_db["equipment_id"], falla_id=falla_a["id"]
    )
    second = await create_procedimiento(
        client, headers, test_db["equipment_id"], falla_id=falla_a["id"]
    )
    assert first.status_code == 200 and second.status_code == 200

    monkeypatch.setattr(
        "app.agents.reporte_agent.reporte_agent", StubReporteAgent(CONSUMER_CONTENIDO)
    )
    with pytest.raises(MultipleResultsFound):
        await client.post(f"/api/reportes/generar/{falla_a['id']}", headers=headers)
