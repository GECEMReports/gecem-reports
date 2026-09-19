import asyncio
import sys

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.checkpoint import checkpoint_dsn


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main() -> None:
    async with AsyncPostgresSaver.from_conn_string(checkpoint_dsn()) as checkpointer:
        await checkpointer.setup()
    print("LangGraph checkpoint tables are ready.")


if __name__ == "__main__":
    asyncio.run(main())
