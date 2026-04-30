# user-app

FastAPI SQLite user CRUD API for a `User` model with SQLite persistence.

## Setup

1. Install dependencies:
   - `python3 -m pip install -r requirements.txt`
2. Configure environment (local):
   - Copy `.env.example` to `.env` in this directory.
   - Set `OPENAI_API_KEY` for live plan generation (optional `OPENAI_MODEL`, `DATABASE_URL`, `PLAN_GENERATION_TIMEOUT_SECONDS`). `.env` is gitignored.
3. Run migrations:
   - `python3 -m alembic upgrade head`
4. Start API server (from this directory):
   - `python3 -m uvicorn app.main:app --reload`

## API Docs

- Swagger UI: `http://127.0.0.1:8000/docs`

## Test

- `python3 -m pytest -q`
