from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.agents.llm import get_llm_structured


# --- Structured output schemas ---
class CotizacionGenerada(BaseModel):
    """Cotización generada por el agente."""
    subtotal_refacciones: float = Field(description="Suma total de refacciones")
    notas: str = Field(default="", description="Notas o justificación de la cotización")


# --- State ---
class CotizacionAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    falla_id: str
    parte: str
    pieza: str
    descripcion: str
    marca: str
    modelo: str
    refacciones: list[dict]
    subtotal_refacciones: float
    mano_de_obra: float
    total: float
    moneda: str
    notas: str
    pregunta_mano_obra: bool


# --- Nodes ---
async def calcular_refacciones(state: CotizacionAgentState) -> dict:
    """Calculate subtotal from refacciones."""
    subtotal = sum(
        (r.get("precio_unitario", 0) or 0) * r.get("cantidad", 1)
        for r in state.get("refacciones", [])
    )
    return {"subtotal_refacciones": subtotal, "moneda": "MXN"}


def preguntar_mano_obra(state: CotizacionAgentState) -> Command:
    """Ask mechanic for labor cost using interrupt()."""
    respuesta = interrupt({
        "pregunta": f"Las refacciones suman ${state['subtotal_refacciones']:,.2f} {state['moneda']}. ¿Cuánto cobras por mano de obra?",
        "subtotal_refacciones": state["subtotal_refacciones"],
        "moneda": state["moneda"],
    })

    # Parse the response - could be a number or a dict with amount and notes
    if isinstance(respuesta, dict):
        mano_de_obra = float(respuesta.get("monto", 0))
        notas_extra = respuesta.get("notas", "")
    else:
        mano_de_obra = float(respuesta)
        notas_extra = ""

    total = state["subtotal_refacciones"] + mano_de_obra
    notas = state.get("notas", "")
    if notas_extra:
        notas = f"{notas}\n{notas_extra}".strip()

    return Command(
        update={
            "mano_de_obra": mano_de_obra,
            "total": total,
            "notas": notas,
            "pregunta_mano_obra": False,
        },
    )


async def generar_cotizacion(state: CotizacionAgentState) -> dict:
    """Generate final quote with LLM for professional notes."""
    llm = get_llm_structured()

    refacciones_text = "\n".join(
        f"- {r.get('nombre', 'N/A')}: x{r.get('cantidad', 1)} a ${r.get('precio_unitario', 0):,.2f} {state['moneda']}"
        for r in state.get("refacciones", [])
    ) if state.get("refacciones") else "Sin refacciones."

    response = await llm.ainvoke([
        SystemMessage(content=(
            "Eres un asistente administrativo de un taller de maquinaria pesada. "
            "Genera una nota profesional breve para una cotización de reparación. "
            "Incluye: resumen del trabajo, justificación del costo, y condiciones. "
            "Responde en español, máximo 3 oraciones."
        )),
        HumanMessage(content=(
            f"Equipo: {state['marca']} {state['modelo']}\n"
            f"Falla: {state['parte']} - {state['pieza']}\n"
            f"Descripción: {state['descripcion']}\n"
            f"Refacciones:\n{refacciones_text}\n"
            f"Subtotal refacciones: ${state['subtotal_refacciones']:,.2f} {state['moneda']}\n"
            f"Mano de obra: ${state['mano_de_obra']:,.2f} {state['moneda']}\n"
            f"Total: ${state['total']:,.2f} {state['moneda']}"
        )),
    ])

    notas = response.content if hasattr(response, 'content') else str(response)
    return {"notas": notas}


# --- Graph ---
def build_cotizacion_agent():
    graph = StateGraph(CotizacionAgentState)

    graph.add_node("calcular", calcular_refacciones)
    graph.add_node("preguntar_mano_obra", preguntar_mano_obra)
    graph.add_node("generar", generar_cotizacion)

    graph.add_edge(START, "calcular")
    graph.add_edge("calcular", "preguntar_mano_obra")
    graph.add_edge("preguntar_mano_obra", "generar")
    graph.add_edge("generar", END)

    return graph.compile()


cotizacion_agent = build_cotizacion_agent()
