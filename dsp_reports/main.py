import uvicorn
import asyncio

from fastapi import FastAPI

from dsp_reports.app.routers.discovery import router as discovery_router


app = FastAPI()#servers=[{"url": get_settings().vite_app_api_url}])


app.include_router(
    discovery_router,
    tags=["reporting"],
)


if __name__ == "__main__":
    server = uvicorn.Server(config=uvicorn.Config(app, workers=1, loop="asyncio", host="0.0.0.0", port=5002))
    asyncio.run(server.serve())