# user-app

FastAPI SQLite user CRUD API for a `User` model with SQLite persistence.

## Setup

1. Install dependencies:
   - `python3 -m pip install -r requirements.txt`
2. Run migrations:
   - `python3 -m alembic upgrade head`
3. Start API server:
   - `python3 -m uvicorn app.main:app --reload`

## API Docs

- Swagger UI: `http://127.0.0.1:8000/docs`

## Test

- `python3 -m pytest -q`
