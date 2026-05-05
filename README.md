# user-app

FastAPI API with SQLAlchemy. **Local:** SQLite via `.env`. **Production (Render):** Postgres (e.g. Neon) via host environment variables only.

## Local setup

1. Install dependencies: `python3 -m pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and keep `DATABASE_URL=sqlite:///./app.db` for local testing.
3. Run migrations: `python3 -m alembic upgrade head`
4. Start API: `python3 -m uvicorn app.main:app --reload`

## Production on Render

This repo is **only the API**. The frontend lives in a **separate repository**; point it at this service via `VITE_API_BASE_URL` (or equivalent) once deployed.

[`render.yaml`](./render.yaml) sits at the **root of this repo** — Render picks it up automatically for **New → Blueprint** (no custom path needed).

1. In [Render](https://dashboard.render.com), **New → Blueprint** and connect **this** (`user-app`) repository.
2. After the web service is created, open **Environment** and add **synchronously** (never commit these):
   - **`DATABASE_URL`** — Neon URI, e.g. `postgresql+psycopg2://USER:PASS@HOST/neondb?sslmode=require`
   - **`OPENAI_API_KEY`** — required for live plan generation
   - **`CORS_ORIGINS`** — comma-separated frontend URLs, e.g. `https://your-frontend.onrender.com` (no trailing slash). Localhost stays allowed for dev builds.
   - Optional: `OPENAI_MODEL`, `PLAN_GENERATION_TIMEOUT_SECONDS`, `LOG_LEVEL`
3. **Deploy:** `buildCommand` installs deps; **`preDeployCommand`** runs `alembic upgrade head`; **`startCommand`** runs Uvicorn on `$PORT`.
4. Smoke test: open `https://<your-service>.onrender.com/docs` and run signup / plan generate.

**SQLite stays local:** production uses only the Render **Environment** tab — your machine keeps `.env` with SQLite.

## API docs (local)

- Swagger UI: `http://127.0.0.1:8000/docs`

## Test

- `python3 -m pytest -q`
