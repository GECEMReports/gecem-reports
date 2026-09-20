import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from app.main import app

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting GECEM API on {host}:{port}", flush=True)
    config = uvicorn.Config(app, host=host, port=port, reload=False, log_level="info")
    server = uvicorn.Server(config)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(server.serve())
