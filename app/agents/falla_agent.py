from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.agents.llm import get_llm_structured


# --- Structured output schemas ---
class FallaEstructurada(BaseModel):
    """Estructura de una falla real detectada en maquinaria pesada."""
    parte: str = Field(description="Parte del equipo afectada (ej: Motor, Brazo de Boom, Hidráulico)")
    pieza: str = Field(description="Pieza específica con la falla (ej: Bomba piloto, Cilindro hidráulico)")
    descripcion: str = Field(description="Descripción detallada de la falla encontrada")
    causa_raiz: str = Field(description="Causa raíz probable de la falla")
    prioridad: str = Field(description="Prioridad: baja, normal, urgente, critica")
    severidad: str = Field(description="Severidad del daño: leve, moderado, severo, critico")


# --- State ---
class FallaAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    diagnostico_ia: str
    descripcion_mecanico: str
    marca: str
    modelo: str
    horas: float
    falla_estructurada: dict
    necesita_mas_info: bool
    pregunta_seguimiento: str


# --- Nodes ---
async def check_info(state: FallaAgentState) -> dict:
    """Check if we have enough info to structure the failure."""
    llm = get_llm_structured()
    structured_llm = llm.with_structured_output(FallaCheckResult)

    result = await structured_llm.ainvoke([
        SystemMessage(content=(
            "Eres un mecánico senior. Evalúa si tienes suficiente información para "
            "estructurar una falla de maquinaria pesada. Necesitas saber:\n"
            "1. Qué parte del equipo está afectada\n"
            "2. Qué pieza específica tiene la falla\n"
            "3. Descripción clara del daño\n\n"
            "Si falta información crítica, indica qué necesitas saber."
        )),
        HumanMessage(content=(
            f"Diagnóstico IA previo: {state['diagnostico_ia']}\n"
            f"Descripción del mecánico: {state['descripcion_mecanico']}\n"
            f"Equipo: {state['marca']} {state['modelo']} ({state['horas']} hrs)"
        )),
    ])

    return {
        "necesita_mas_info": result.necesita_mas_info,
        "pregunta_seguimiento": result.pregunta if result.necesita_mas_info else "",
    }


class FallaCheckResult(BaseModel):
    """Resultado de verificación de información."""
    necesita_mas_info: bool = Field(description="Si se necesita más información")
    pregunta: str = Field(default="", description="Pregunta para obtener la info faltante")


async def estructurar_falla(state: FallaAgentState) -> dict:
    """Structure the failure using the LLM with structured output."""
    llm = get_llm_structured()
    structured_llm = llm.with_structured_output(FallaEstructurada)

    result = await structured_llm.ainvoke([
        SystemMessage(content=(
            "Eres un mecánico senior de maquinaria pesada. Con base en el diagnóstico de IA "
            "y la descripción del mecánico, estructura la falla real encontrada.\n\n"
            "Clasifica la prioridad así:\n"
            "- baja: no afecta operación inmediata\n"
            "- normal: afecta rendimiento pero puede seguir operando\n"
            "- urgente: necesita reparación pronto o empeora\n"
            "- critica: máquina no puede operar de forma segura\n\n"
            "Clasifica la severidad así:\n"
            "- leve: desgaste normal, mantenimiento menor\n"
            "- moderado: requiere reparación, no urgente\n"
            "- severo: daño significativo, reparación mayor\n"
            "- critico: posible falla catastrófica"
        )),
        HumanMessage(content=(
            f"Equipo: {state['marca']} {state['modelo']} ({state['horas']} hrs)\n\n"
            f"Diagnóstico IA:\n{state['diagnostico_ia']}\n\n"
            f"Descripción del mecánico (falla real encontrada):\n{state['descripcion_mecanico']}"
        )),
    ])

    return {
        "falla_estructurada": {
            "parte": result.parte,
            "pieza": result.pieza,
            "descripcion": result.descripcion,
            "causa_raiz": result.causa_raiz,
            "prioridad": result.prioridad,
            "severidad": result.severidad,
        }
    }


# --- Conditional edge ---
def route_after_check(state: FallaAgentState) -> str:
    if state.get("necesita_mas_info"):
        return "end_with_question"
    return "estructurar"


# --- Graph ---
def build_falla_agent():
    graph = StateGraph(FallaAgentState)

    graph.add_node("check_info", check_info)
    graph.add_node("estructurar", estructurar_falla)

    graph.add_edge(START, "check_info")
    graph.add_conditional_edges(
        "check_info",
        route_after_check,
        {
            "estructurar": "estructurar",
            "end_with_question": END,
        },
    )
    graph.add_edge("estructurar", END)

    return graph.compile()


falla_agent = build_falla_agent()
