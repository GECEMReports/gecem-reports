"""ETAPA 0 — Tests de contrato y regresion del dominio Diagnosis.

Cubre el comportamiento ACTUAL de POST /api/ai/diagnose, las herramientas
de `app/agents/tools.py` y la carga del CSV, SIN cambiar codigo productivo.

El LLM (DeepSeek) jamas se invoca: `diagnosis_agent.ainvoke` siempre se
sustituye por un stub. Ninguna prueba toca la base de desarrollo.
"""

import uuid

import pytest
from langgraph.types import Command

import app.modules.diagnosis.agent as diagnosis_agent_module
from app.modules.diagnosis.tools import (
    _ALL_FAILURES,
    _load_failures_from_csv,
    get_common_failures,
    search_equipment_history,
)
from app.database import async_session
from app.modules.diagnosis.models import Report
from sqlalchemy import select

from conftest import tenant_headers

pytestmark = pytest.mark.anyio

SUCCESS_STATE = {
    "symptoms": "humo negro y perdida de potencia",
    "diagnosis": "inyectores obstruidos",
    "recommendations": ["revisar inyectores", "cambiar filtro de combustible"],
    "parts_needed": ["filtro de combustible"],
    "estimated_hours": 2.5,
    "problem_type": "motor",
    "severity": "high",
    "necesita_mas_info": False,
}


class StubAgent:
    """Sustituto del grafo LangGraph: registra llamadas, nunca llama al LLM."""

    def __init__(self, final_state):
        self.final_state = final_state
        self.calls = []

    async def ainvoke(self, payload, config=None):
        self.calls.append({"input": payload, "config": config})
        return self.final_state


def patch_agent(monkeypatch, final_state):
    stub = StubAgent(final_state)
    monkeypatch.setattr(diagnosis_agent_module, "diagnosis_agent", stub)
    return stub


# 1. Diagnostico exitoso -----------------------------------------------------
async def test_diagnose_success(client, test_db, monkeypatch):
    stub = patch_agent(monkeypatch, dict(SUCCESS_STATE))
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "humo negro"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["diagnosis"] == "inyectores obstruidos"
    assert body["problem_type"] == "motor"
    assert body["recommendations"] == ["revisar inyectores", "cambiar filtro de combustible"]
    assert body["parts_needed"] == ["filtro de combustible"]
    assert body["estimated_hours"] == 2.5
    assert body["severity"] == "high"
    assert body["necesita_mas_info"] is False
    assert body["interrupted"] is False
    assert body["thread_id"]
    assert len(stub.calls) == 1


# 2. El schema de respuesta se mantiene exacto --------------------------------
async def test_diagnose_success_schema_keys(client, test_db, monkeypatch):
    patch_agent(monkeypatch, dict(SUCCESS_STATE))
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "humo negro"},
        headers=headers,
    )
    assert res.status_code == 200
    assert set(res.json().keys()) == {
        "interrupted",
        "thread_id",
        "necesita_mas_info",
        "problem_type",
        "diagnosis",
        "recommendations",
        "parts_needed",
        "estimated_hours",
        "severity",
    }


# 3. Rama interrupted ----------------------------------------------------------
async def test_diagnose_interrupted(client, test_db, monkeypatch):
    final_state = {"__interrupt__": [{"pregunta": "¿El equipo presenta fugas visibles?"}]}
    patch_agent(monkeypatch, final_state)
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "ruido raro"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["interrupted"] is True
    assert body["pregunta"] == "¿El equipo presenta fugas visibles?"
    assert body["thread_id"]
    assert set(body.keys()) == {"interrupted", "thread_id", "pregunta"}


# 4. Rama necesita_mas_info ----------------------------------------------------
async def test_diagnose_needs_more_info(client, test_db, monkeypatch):
    final_state = {
        "necesita_mas_info": True,
        "pregunta_seguimiento": "¿Desde cuando ocurre la falla?",
    }
    patch_agent(monkeypatch, final_state)
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "vibra"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["necesita_mas_info"] is True
    assert body["pregunta_seguimiento"] == "¿Desde cuando ocurre la falla?"
    assert set(body.keys()) == {
        "interrupted",
        "thread_id",
        "necesita_mas_info",
        "pregunta_seguimiento",
    }


# 5. Conservacion y reanudacion mediante thread_id ------------------------------
async def test_diagnose_resume_with_thread_id(client, test_db, monkeypatch):
    stub = patch_agent(monkeypatch, dict(SUCCESS_STATE))
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={
            "equipment_id": str(test_db["equipment_id"]),
            "thread_id": "thread-abc-123",
            "respuesta_seguimiento": "si, hay fuga de aceite",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["thread_id"] == "thread-abc-123"
    assert body["diagnosis"] == "inyectores obstruidos"
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert isinstance(call["input"], Command)
    assert getattr(call["input"], "resume", None) == "si, hay fuga de aceite"
    assert call["config"] == {"configurable": {"thread_id": "thread-abc-123"}}


async def test_diagnose_generates_thread_id_when_missing(client, test_db, monkeypatch):
    stub = patch_agent(monkeypatch, dict(SUCCESS_STATE))
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "humo"},
        headers=headers,
    )
    assert res.status_code == 200
    thread_id = res.json()["thread_id"]
    uuid.UUID(thread_id)
    assert stub.calls[0]["config"] == {"configurable": {"thread_id": thread_id}}


# 6. 400 cuando falta tenant -----------------------------------------------------
async def test_diagnose_missing_tenant_returns_400(client, test_db, monkeypatch):
    stub = patch_agent(monkeypatch, dict(SUCCESS_STATE))
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "humo"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Tenant context required"
    assert stub.calls == []


# 7. 404 para equipment fuera del tenant ------------------------------------------
async def test_diagnose_unknown_equipment_returns_404(client, test_db, monkeypatch):
    stub = patch_agent(monkeypatch, dict(SUCCESS_STATE))
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(uuid.uuid4()), "symptoms": "humo"},
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Equipment not found"
    assert stub.calls == []


# 8. 422 request invalido / sin symptoms --------------------------------------------
@pytest.mark.parametrize("symptoms", [None, "", "   "])
async def test_diagnose_missing_symptoms_returns_422(client, test_db, monkeypatch, symptoms):
    stub = patch_agent(monkeypatch, dict(SUCCESS_STATE))
    headers = tenant_headers(test_db["tenant_id"])
    payload = {"equipment_id": str(test_db["equipment_id"])}
    if symptoms is not None:
        payload["symptoms"] = symptoms
    res = await client.post("/api/ai/diagnose", json=payload, headers=headers)
    assert res.status_code == 422
    assert res.json()["detail"] == "symptoms is required for a new diagnosis"
    assert stub.calls == []


# 9. 503 si el agente no esta inicializado ----------------------------------------------
async def test_diagnose_uninitialized_agent_returns_503(client, test_db):
    assert diagnosis_agent_module.diagnosis_agent is None
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "humo"},
        headers=headers,
    )
    assert res.status_code == 503
    assert res.json()["detail"] == "Diagnosis agent is not initialized"


# 10. Persistencia de Report con tenant_id correcto ---------------------------------------
async def test_diagnose_persists_report_with_tenant(client, test_db, monkeypatch):
    patch_agent(monkeypatch, dict(SUCCESS_STATE))
    headers = tenant_headers(test_db["tenant_id"])
    res = await client.post(
        "/api/ai/diagnose",
        json={"equipment_id": str(test_db["equipment_id"]), "symptoms": "humo negro"},
        headers=headers,
    )
    assert res.status_code == 200
    async with async_session() as session:
        result = await session.execute(
            select(Report).where(Report.equipment_id == str(test_db["equipment_id"]))
        )
        reports = result.scalars().all()
    assert len(reports) == 1
    report = reports[0]
    assert report.tenant_id == test_db["tenant_id"]
    assert report.report_type == "diagnosis"
    assert report.status == "completed"
    assert report.diagnosis == "inyectores obstruidos"
    assert "revisar inyectores" in (report.recommendations or "")


# 11. search_equipment_history ---------------------------------------------------------------
async def test_search_equipment_history(test_db):
    async with async_session() as session:
        session.add(
            Report(
                tenant_id=test_db["tenant_id"],
                equipment_id=str(test_db["equipment_id"]),
                title="Diagnostico: CAT 320D",
                report_type="diagnosis",
                symptoms="humo",
                diagnosis="inyectores",
                status="completed",
            )
        )
        await session.commit()

    result = await search_equipment_history(str(test_db["equipment_id"]))
    assert result["equipment"]["brand"] == "CAT"
    assert result["equipment"]["model"] == "320D"
    assert result["equipment"]["serial_number"] == "SN-TEST-001"
    assert result["equipment"]["type"] == "excavator"
    assert result["equipment"]["hours"] == 1250.0
    assert result["equipment"]["year"] == 2019
    assert len(result["history"]) == 1
    assert result["history"][0]["title"] == "Diagnostico: CAT 320D"
    assert result["history"][0]["diagnosis"] == "inyectores"


async def test_search_equipment_history_unknown_id():
    result = await search_equipment_history(str(uuid.uuid4()))
    assert result == {"error": "Equipment not found"}


# 12. Carga de fallas_historicas.csv ------------------------------------------------------------------
def test_csv_loads_with_expected_shape():
    rows = _load_failures_from_csv()
    assert len(rows) > 0
    expected_keys = {"marca", "modelo", "parte", "pieza", "falla", "solution", "status"}
    for row in rows:
        assert set(row.keys()) == expected_keys
        assert all(isinstance(v, str) and v for v in row.values())
    assert len(_ALL_FAILURES) == len(rows)


def test_get_common_failures_matches_csv_row():
    first = _load_failures_from_csv()[0]
    result = get_common_failures(first["marca"], first["modelo"])
    assert result["brand"] == first["marca"]
    assert result["model"] == first["modelo"]
    assert len(result["common_failures"]) >= 1
    assert all("failure" in item and "solution" in item for item in result["common_failures"])


def test_get_common_failures_unknown_brand_returns_empty():
    result = get_common_failures("MarcaInexistenteXYZ", "ModeloInexistenteXYZ")
    assert result["common_failures"] == []
