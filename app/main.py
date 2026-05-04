from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

from contextlib import asynccontextmanager
from typing import Dict

import logging

from fastapi import FastAPI

from app.logging_config import setup_app_logging
from app.middleware.request_logging import RequestLoggingMiddleware

setup_app_logging()

from app.api.routes.auth import router as auth_router
from app.api.routes.plan import router as plan_router
from app.api.routes.users import router as users_router

from starlette.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("user-app: application startup")
    yield
    logger.info("user-app: application shutdown")


app = FastAPI(title="user-app", version="1.0.0", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(plan_router)
app.include_router(users_router)


@app.get("/health", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}
