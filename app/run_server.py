import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from app.main import app


if __name__ == "__main__":
    print("Starting GECEM API", flush=True)
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, reload=False, log_level="info")
    server = uvicorn.Server(config)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(server.serve())
