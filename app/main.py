from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

from typing import Dict

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.plan import router as plan_router
from app.api.routes.users import router as users_router

from starlette.middleware.cors import CORSMiddleware


app = FastAPI(title="user-app", version="1.0.0")
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
