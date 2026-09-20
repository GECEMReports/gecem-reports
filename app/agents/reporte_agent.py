from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.agents.llm import get_llm_structured


# --- Structured output schemas ---
class ReporteContenido(BaseModel):
    """Contenido del reporte para el cliente."""
    resumen_ejecutivo: str = Field(description="Resumen del trabajo realizado en 2-3 oraciones")
    diagnostico: str = Field(description="Qué se encontró durante la inspección")
    trabajo_realizado: str = Field(description="Qué se hizo para reparar")
    refacciones_utilizadas: str = Field(description="Lista de refacciones usadas")
    recomendaciones: str = Field(description="Recomendaciones para el cliente")
    garantia: str = Field(description="Condiciones de garantía del trabajo")


# --- State ---
class ReporteAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    falla_id: str
    parte: str
    pieza: str
    descripcion: str
    causa_raiz: str
    marca: str
    modelo: str
    horas: float
    refacciones: list[dict]
    pasos: list[dict]
    tiempo_total: float
    contenido: dict


# --- Nodes ---
async def generar_reporte(state: ReporteAgentState) -> dict:
    """Generate client report content using LLM."""
    llm = get_llm_structured().with_structured_output(ReporteContenido)

    refacciones_text = "\n".join(
        f"- {r.get('nombre', 'N/A')} x{r.get('cantidad', 1)}"
        for r in state.get("refacciones", [])
    ) if state.get("refacciones") else "Sin refacciones utilizadas."

    pasos_text = "\n".join(
        f"{p.get('numero_paso', i+1)}. {p.get('descripcion', '')} ({p.get('tiempo_minutos', 0)} min)"
        for i, p in enumerate(state.get("pasos", []))
    ) if state.get("pasos") else "Sin pasos documentados."

    response = await llm.ainvoke([
        SystemMessage(content=(
            "Eres un redactor técnico profesional que genera reportes de reparación para clientes "
            "de maquinaria pesada. El reporte debe ser claro, profesional y fácil de entender para "
            "un propietario de equipo que no es mecánico.\n\n"
            "El tono debe ser formal pero accesible. Evita jerga técnica excesiva. "
            "Responde en español."
        )),
        HumanMessage(content=(
            f"Equipo: {state['marca']} {state['modelo']} ({state['horas']} hrs)\n"
            f"Falla: {state['parte']} - {state['pieza']}\n"
            f"Descripción: {state['descripcion']}\n"
            f"Causa raíz: {state['causa_raiz']}\n\n"
            f"Refacciones utilizadas:\n{refacciones_text}\n\n"
            f"Pasos de reparación:\n{pasos_text}\n\n"
            f"Tiempo total: {state['tiempo_total']} horas"
        )),
    ])

    return {
        "contenido": {
            "resumen_ejecutivo": response.resumen_ejecutivo,
            "diagnostico": response.diagnostico,
            "trabajo_realizado": response.trabajo_realizado,
            "refacciones_utilizadas": response.refacciones_utilizadas,
            "recomendaciones": response.recomendaciones,
            "garantia": response.garantia,
        }
    }


# --- Graph ---
def build_reporte_agent():
    graph = StateGraph(ReporteAgentState)

    graph.add_node("generar", generar_reporte)
    graph.add_edge(START, "generar")
    graph.add_edge("generar", END)

    return graph.compile()


reporte_agent = build_reporte_agent()
