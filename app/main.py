import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import scheduler as sched
from app.db import init_db
from app.routes.ui import router as ui_router
from app.webhook import router as webhook_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sched.start()
    try:
        yield
    finally:
        sched.shutdown()


app = FastAPI(title="LINE Group Scheduler Bot", lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(ui_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
