from typing import Dict

from fastapi import FastAPI

from app.api.routes.users import router as users_router


app = FastAPI(title="user-app", version="1.0.0")
app.include_router(users_router)


@app.get("/health", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}
