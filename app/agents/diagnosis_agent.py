from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from app.agents.llm import get_llm, get_llm_structured
from app.agents.tools import get_common_failures, search_equipment_history

DEMO_MODE = False


# --- Tools ---
@tool
async def get_equipment_info(equipment_id: str) -> dict:
    """Get equipment details and repair history from the database."""
    return await search_equipment_history(equipment_id)


@tool
def lookup_common_failures(brand: str, model: str) -> dict:
    """Look up known common failures for a specific equipment brand and model."""
    return get_common_failures(brand, model)


# --- State ---
class DiagnosisState(TypedDict):
    messages: Annotated[list, add_messages]
    equipment_id: str
    symptoms: str
    equipment_info: dict
    diagnosis: str
    recommendations: list[str]
    parts_needed: list[str]
    estimated_hours: float
    severity: str
    problem_type: str
    necesita_mas_info: bool
    pregunta_seguimiento: str
    detail_rounds: int


class DetailEvaluation(BaseModel):
    suficiente: bool = Field(description="Si los síntomas son suficientes para diagnosticar")
    pregunta: str = Field(default="", description="Pregunta concreta para obtener información faltante")


class DiagnosisOutput(BaseModel):
    diagnosis: str
    recommendations: list[str]
    parts_needed: list[str]
    estimated_hours: float
    severity: str


# --- Demo helpers ---
def _demo_classify(symptoms: str) -> str:
    s = symptoms.lower()
    if any(w in s for w in ["motor", "engine", "acelerar", "humo", "aceite", "pistón", "cilindro"]):
        return "engine"
    if any(w in s for w in ["hidraulic", "brazo", "cuchara", "presión", "fuga", "cilindro hidráulico"]):
        return "hydraulic"
    if any(w in s for w in ["eléctric", "batería", "luz", "sensor", "cable", "fusible"]):
        return "electrical"
    if any(w in s for w in ["transmisión", "marcha", "velocidad", "embrague", "diferencial"]):
        return "transmission"
    if any(w in s for w in ["oruga", "chasis", "estructura", "soldadura", "grieta"]):
        return "structural"
    return "other"


def _demo_diagnose(problem_type: str, symptoms: str, equipment: dict) -> dict:
    brand = equipment.get("brand", "Unknown")
    model = equipment.get("model", "Unknown")
    hours = equipment.get("hours", 0)

    demos = {
        "engine": {
            "diagnosis": (
                f"Diagnóstico para {brand} {model} ({hours} hrs): "
                f"Los síntomas descritos ({symptoms}) indican desgaste en anillos de pistón y posible obstrucción "
                f"en el sistema de inyección. La pérdida de potencia acompañada de humo negro sugiere "
                f"combustión incompleta. Se recomienda prueba de compresión en los 6 cilindros."
            ),
            "recommendations": [
                "Realizar prueba de compresión en todos los cilindros",
                "Inspeccionar y limpiar/inyectores de combustible",
                "Verificar filtro de aire y reemplazar si es necesario",
                "Cambiar aceite de motor y filtro",
                "Revisar turbo y mangueras de admisión",
            ],
            "parts_needed": [
                "Kit de anillos de pistón",
                "Inyectores de combustible (juego)",
                "Filtro de aire",
                "Filtro de aceite",
                "Aceite de motor 15W-40 (20L)",
            ],
            "estimated_hours": 8.0,
            "severity": "high",
        },
        "hydraulic": {
            "diagnosis": (
                f"Diagnóstico para {brand} {model} ({hours} hrs): "
                f"Se detecta fuga en el sistema hidráulico. El brazo pierde posición bajo carga, "
                f"lo que indica desgaste en sellos del cilindro principal o válvula de control. "
                f"Presión hidráulica por debajo de especificaciones."
            ),
            "recommendations": [
                "Medir presión hidráulica en puntos de prueba",
                "Inspeccionar cilindros hidráulicos en busca de fugas externas",
                "Revisar bomba hidráulica y sellos",
                "Verificar nivel y condición del aceite hidráulico",
                "Inspeccionar mangueras y conexiones",
            ],
            "parts_needed": [
                "Kit de sellos para cilindro hidráulico",
                "Aceite hidráulico ISO 46 (40L)",
                "Filtro hidráulico",
                "Manguera hidráulica 3/4\" (2m)",
            ],
            "estimated_hours": 6.0,
            "severity": "medium",
        },
        "electrical": {
            "diagnosis": (
                f"Diagnóstico para {brand} {model} ({hours} hrs): "
                f"Fallas eléctricas detectadas. Posible cortocircuito o sensor defectuoso. "
                f"Verificar arnés de cables y conexiones a tierra."
            ),
            "recommendations": [
                "Escanear códigos de falla con herramienta de diagnóstico",
                "Inspeccionar arnés de cables en busca de daños",
                "Probar alternador y regulador de voltaje",
                "Verificar batería y bornes",
            ],
            "parts_needed": [
                "Batería 12V 200Ah",
                "Kit de terminales eléctricos",
                "Cableado AWG 4 (5m)",
            ],
            "estimated_hours": 4.0,
            "severity": "medium",
        },
        "transmission": {
            "diagnosis": (
                f"Diagnóstico para {brand} {model} ({hours} hrs): "
                f"La transmisión presenta patinamiento en marchas. El fluido de transmisión "
                f"está oscurecido y con olor a quemado. Desgaste probable en discos de embrague."
            ),
            "recommendations": [
                "Cambiar fluido de transmisión y filtro",
                "Inspeccionar discos de embrague",
                "Revisar convertidor de par",
                "Probar presiones de línea de transmisión",
            ],
            "parts_needed": [
                "Filtro de transmisión",
                "Fluido de transmisión ATF (20L)",
                "Kit de discos de embrague",
            ],
            "estimated_hours": 12.0,
            "severity": "high",
        },
        "structural": {
            "diagnosis": (
                f"Diagnóstico para {brand} {model} ({hours} hrs): "
                f"Se observan grietas en la estructura principal. "
                f"Posible fatiga del material por sobrecarga o impacto."
            ),
            "recommendations": [
                "Inspección visual completa de la estructura",
                "Medir grietas con penetrante fluorescente",
                "Evaluar necesidad de refuerzo o soldadura",
                "No operar hasta completar reparación",
            ],
            "parts_needed": [
                "Electrodos de soldadura 7018",
                "Placa de refuerzo acero A36",
            ],
            "estimated_hours": 10.0,
            "severity": "critical",
        },
        "other": {
            "diagnosis": (
                f"Diagnóstico para {brand} {model} ({hours} hrs): "
                f"Se requiere inspección adicional para determinar la causa raíz "
                f"de los síntomas reportados: {symptoms}."
            ),
            "recommendations": [
                "Inspección visual completa del equipo",
                "Revisar historial de mantenimiento",
                "Consultar manual del fabricante",
            ],
            "parts_needed": [],
            "estimated_hours": 2.0,
            "severity": "low",
        },
    }
    return demos.get(problem_type, demos["other"])


# --- Nodes ---
async def evaluate_detail(state: DiagnosisState) -> dict:
    """Evaluate detail without pausing; pausing is isolated in ask_detail."""
    if state.get("detail_rounds", 0) >= 2:
        return {"necesita_mas_info": False, "pregunta_seguimiento": ""}

    if DEMO_MODE:
        symptoms = state["symptoms"].lower()
        vague_keywords = ["no jala", "no funciona", "mal", "ruido", "falla", "problema"]
        is_vague = len(state["symptoms"]) < 30 or any(k in symptoms for k in vague_keywords)
        if is_vague:
            return {
                "necesita_mas_info": True,
                "pregunta_seguimiento": (
                    "Los síntomas que describes son muy generales. Para poder darte un diagnóstico "
                    "más preciso, necesito que me ayudes con más detalles:\n\n"
                    "1. ¿En qué momento ocurre el problema? (al arrancar, bajo carga, al girar, etc.)\n"
                    "2. ¿Hay ruidos específicos? (golpeteo, silbido, chirrido, etc.)\n"
                    "3. ¿Hay fugas visibles? (aceite hidráulico, refrigerante, combustible)\n"
                    "4. ¿El problema es constante o intermitente?\n"
                    "5. ¿Cuándo fue el último servicio o mantenimiento?"
                ),
            }
        return {"necesita_mas_info": False, "pregunta_seguimiento": ""}

    structured_llm = get_llm_structured().with_structured_output(DetailEvaluation)
    result = await structured_llm.ainvoke([
        SystemMessage(content=(
            "Eres un mecánico senior de maquinaria pesada. Evalúa si la descripción de síntomas "
            "es suficientemente detallada para generar un diagnóstico confiable. Considera insuficiente "
            "una descripción muy corta, sin contexto de cuándo ocurre, sin ruidos, fugas o comportamiento "
            "específico. Si falta información, formula una pregunta concreta."
        )),
        HumanMessage(content=f"Síntomas reportados: {state['symptoms']}"),
    ])
    return {
        "necesita_mas_info": not result.suficiente,
        "pregunta_seguimiento": result.pregunta if not result.suficiente else "",
    }


def check_detail(state: DiagnosisState) -> Command:
    """Pause for the mechanic; this node contains no LLM work before interrupt()."""
    if not state.get("necesita_mas_info"):
        return Command(goto="classify")

    answer = interrupt({
        "pregunta": state["pregunta_seguimiento"],
        "ronda": state.get("detail_rounds", 0) + 1,
    })
    return Command(
        goto="evaluate_detail",
        update={
            "symptoms": f"{state['symptoms']}\n\nInformación adicional: {answer}",
            "detail_rounds": state.get("detail_rounds", 0) + 1,
            "necesita_mas_info": False,
            "pregunta_seguimiento": "",
        },
    )


async def classify_problem(state: DiagnosisState) -> dict:
    """Classify the type of problem based on symptoms."""
    if DEMO_MODE:
        problem_type = _demo_classify(state["symptoms"])
        return {"problem_type": problem_type}

    llm = get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=(
            "You are a heavy machinery expert. Classify the problem type based on symptoms. "
            "Respond with ONLY one word: engine, hydraulic, electrical, transmission, structural, or other."
        )),
        HumanMessage(content=f"Symptoms: {state['symptoms']}"),
    ])
    problem_type = response.content.strip().lower()
    if problem_type not in ("engine", "hydraulic", "electrical", "transmission", "structural", "other"):
        problem_type = "other"
    return {"problem_type": problem_type}


async def consult_history(state: DiagnosisState) -> dict:
    """Fetch equipment history from the database."""
    info = await search_equipment_history(state["equipment_id"])
    return {"equipment_info": info}


async def diagnose(state: DiagnosisState) -> dict:
    """Generate diagnosis using LLM with equipment context."""
    equipment = state.get("equipment_info", {}).get("equipment", {})

    if DEMO_MODE:
        result = _demo_diagnose(state["problem_type"], state["symptoms"], equipment)
        return result

    structured_llm = get_llm_structured().with_structured_output(DiagnosisOutput)

    history = state.get("equipment_info", {}).get("history", [])
    brand = equipment.get("brand", "Unknown")
    model = equipment.get("model", "Unknown")

    common = get_common_failures(brand, model)

    history_text = "\n".join(
        f"- {h['title']} ({h['type']}): {h['symptoms']} -> {h['diagnosis']}"
        for h in history[-5:]
    ) if history else "No previous history."

    common_text = "\n".join(
        f"- {f['failure']}: {f['symptoms']} -> {f['solution']} "
        f"(estatus real: {f['status']})"
        for f in common.get("common_failures", [])
    ) if common.get("common_failures") else "No known common failures."

    result = await structured_llm.ainvoke([
        SystemMessage(content=(
            "You are a senior heavy machinery mechanic. Given the equipment info, symptoms, "
            "history, and known failures, provide a detailed diagnosis.\n\n"
            "Los 'known common failures' son historial real de esta flota. El campo "
            "'estatus real' indica si la solución ya se confirmó (Terminado) o sigue "
            "siendo una hipótesis pendiente (En espera / En trabajo). No presentes una "
            "solución como garantizada si su estatus no es Terminado — trátala como una "
            "pista a investigar, no como un arreglo ya probado."
        )),
        HumanMessage(content=(
            f"Equipment: {brand} {model} ({equipment.get('type', 'N/A')})\n"
            f"Hours: {equipment.get('hours', 'N/A')}\n"
            f"Year: {equipment.get('year', 'N/A')}\n"
            f"Problem type: {state['problem_type']}\n"
            f"Symptoms: {state['symptoms']}\n\n"
            f"Recent history:\n{history_text}\n\n"
            f"Known failures for this model:\n{common_text}"
        )),
    ])

    return {
        "diagnosis": result.diagnosis,
        "recommendations": result.recommendations,
        "parts_needed": result.parts_needed,
        "estimated_hours": result.estimated_hours,
        "severity": result.severity,
    }


# --- Graph ---
def build_diagnosis_graph(checkpointer=None):
    graph = StateGraph(DiagnosisState)

    graph.add_node("evaluate_detail", evaluate_detail)
    graph.add_node("check_detail", check_detail)
    graph.add_node("classify", classify_problem)
    graph.add_node("consult_history", consult_history)
    graph.add_node("diagnose", diagnose)

    graph.add_edge(START, "evaluate_detail")
    graph.add_edge("evaluate_detail", "check_detail")
    graph.add_edge("classify", "consult_history")
    graph.add_edge("consult_history", "diagnose")
    graph.add_edge("diagnose", END)

    return graph.compile(checkpointer=checkpointer)


diagnosis_agent = None


def configure_checkpointer(checkpointer) -> None:
    global diagnosis_agent
    diagnosis_agent = build_diagnosis_graph(checkpointer)
