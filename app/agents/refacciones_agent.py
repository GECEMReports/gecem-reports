from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.agents.llm import get_llm_structured


# --- Structured output schemas ---
class RefaccionSugerida(BaseModel):
    """Refacción sugerida para una reparación."""
    nombre: str = Field(description="Nombre de la refacción")
    numero_parte: str = Field(default="", description="Número de parte si se conoce")
    cantidad: float = Field(description="Cantidad necesaria")
    precio_estimado: float = Field(description="Precio estimado en la moneda indicada")
    moneda: str = Field(description="Moneda: MXN, USD, etc.")
    prioridad: str = Field(description="Prioridad de compra: urgente, normal, preventivo")


class RefaccionesResponse(BaseModel):
    """Lista de refacciones sugeridas."""
    refacciones: list[RefaccionSugerida]
    notas: str = Field(default="", description="Notas adicionales sobre las refacciones")


# --- State ---
class RefaccionesAgentState(TypedDict):
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
    notas: str


# --- Nodes ---
async def sugerir_refacciones(state: RefaccionesAgentState) -> dict:
    """Estimate parts needed for the repair using LLM knowledge."""
    llm = get_llm_structured().with_structured_output(RefaccionesResponse)

    result = await llm.ainvoke([
        SystemMessage(content=(
            "Eres un experto en refacciones de maquinaria pesada. Dada una falla específica "
            "y los datos del equipo, genera una lista de refacciones y consumibles necesarios "
            "para la reparación.\n\n"
            "Para cada refacción incluye:\n"
            "1. Nombre descriptivo\n"
            "2. Número de parte si lo conoces (si no, deja vacío)\n"
            "3. Cantidad necesaria\n"
            "4. Precio estimado de mercado (en la moneda que corresponda)\n"
            "5. Prioridad: urgente (sin esto no arranca), normal (necesario para la reparación), "
            "preventivo (recomendado mientras se tiene abierto)\n\n"
            "Sé realista con los precios. Si no estás seguro de un precio exacto, da un rango "
            "y pon el valor promedio. Responde en español."
        )),
        HumanMessage(content=(
            f"Equipo: {state['marca']} {state['modelo']} ({state['horas']} hrs)\n"
            f"Falla - Parte: {state['parte']}\n"
            f"Falla - Pieza: {state['pieza']}\n"
            f"Descripción: {state['descripcion']}\n"
            f"Causa raíz: {state['causa_raiz']}"
        )),
    ])

    return {
        "refacciones": [r.model_dump() for r in result.refacciones],
        "notas": result.notas,
    }


# --- Graph ---
def build_refacciones_agent():
    graph = StateGraph(RefaccionesAgentState)

    graph.add_node("sugerir", sugerir_refacciones)
    graph.add_edge(START, "sugerir")
    graph.add_edge("sugerir", END)

    return graph.compile()


refacciones_agent = build_refacciones_agent()
