from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.equipment import router as equipment_router
from app.api.ai.diagnosis import router as diagnosis_router
from app.api.ai.falla import router as falla_agent_router
from app.api.ai.refacciones import router as refacciones_router
from app.api.cotizaciones import router as cotizaciones_router
from app.api.reparaciones import router as reparaciones_router
from app.api.reportes import router as reportes_router
from app.api.fallas import router as fallas_router
from app.agents.diagnosis_agent import configure_checkpointer
from app.checkpoint import start_checkpointer, stop_checkpointer
from app.tenancy.middleware import TenantMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    print(f"Event loop: {type(asyncio.get_running_loop()).__name__}", flush=True)
    print("Initializing Postgres checkpointer", flush=True)
    checkpointer = await start_checkpointer()
    print("Postgres checkpointer connected", flush=True)
    configure_checkpointer(checkpointer)
    print("Diagnosis graph configured", flush=True)
    try:
        yield
    finally:
        await stop_checkpointer()


app = FastAPI(
    title="GECEM Reports",
    description="AI-powered heavy machinery reporting platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)

app.include_router(auth_router, prefix="/api")
app.include_router(equipment_router, prefix="/api")
app.include_router(diagnosis_router, prefix="/api")
app.include_router(falla_agent_router, prefix="/api")
app.include_router(refacciones_router, prefix="/api")
app.include_router(cotizaciones_router, prefix="/api")
app.include_router(reparaciones_router, prefix="/api")
app.include_router(reportes_router, prefix="/api")
app.include_router(fallas_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
