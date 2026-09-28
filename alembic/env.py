import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

# El CLI de alembic no agrega la raiz del repo a sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings

# Importa el paquete completo: registra los 13 modelos de negocio en Base.metadata
import app.models  # noqa: F401
from app.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# La URL viene de configuración/env (app.config.settings); nunca de credenciales
# en el repo. ConfigParser interpreta '%' -> se escapa.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))


def include_object(object, name, type_, reflected, compare_to):
    """Excluye del dominio de Alembic: alembic_version y las tablas de
    LangGraph (checkpoint_*) que gestiona langgraph-checkpoint-postgres."""
    if type_ == "table":
        if name == "alembic_version":
            return False
        if name is not None and name.startswith("checkpoint"):
            return False
    return True


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
