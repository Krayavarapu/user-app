# user-app

FastAPI API with SQLAlchemy. **Local:** SQLite via `.env`. **Production (Render):** Postgres (e.g. Neon) via host environment variables only.

## Local setup

1. Install dependencies: `python3 -m pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and keep `DATABASE_URL=sqlite:///./app.db` for local testing.
3. Run migrations: `python3 -m alembic upgrade head`
4. Seed reference data (equipment catalog and exercise library): `python3 -m app.scripts.seed_exercise_library` — idempotent, safe to re-run after editing `app/data/exercise_library/*.json`. An invalid file aborts before touching the database and lists every problem.
5. Start API: `python3 -m uvicorn app.main:app --reload`

## Production on Render

This repo is **only the API**. The frontend lives in a **separate repository**; point it at this service via `VITE_API_BASE_URL` (or equivalent) once deployed.

[`render.yaml`](./render.yaml) sits at the **root of this repo** — Render picks it up automatically for **New → Blueprint** (no custom path needed).

**Python version:** New Render services default to **Python 3.14**, which breaks **`psycopg2-binary`** (C extension / `ImportError: undefined symbol: _PyInterpreterState_Get`). This repo pins **3.12.8** via [`.python-version`](./.python-version) and **`PYTHON_VERSION`** in `render.yaml`. See [Render: Python version](https://render.com/docs/python-version).

1. In [Render](https://dashboard.render.com), **New → Blueprint** and connect **this** (`user-app`) repository.
2. After the web service is created, open **Environment** and add **synchronously** (never commit these):
   - **`DATABASE_URL`** — Neon URI, e.g. `postgresql+psycopg2://USER:PASS@HOST/neondb?sslmode=require`
   - **`OPENAI_API_KEY`** — required for live plan generation
   - **`CORS_ORIGINS`** — comma-separated frontend URLs, e.g. `https://your-frontend.onrender.com` (no trailing slash). Localhost stays allowed for dev builds.
   - Optional: `OPENAI_MODEL`, `PLAN_GENERATION_TIMEOUT_SECONDS`, `LOG_LEVEL`
3. **Deploy:** `buildCommand` installs deps; **`startCommand`** runs `alembic upgrade head`, then `python -m app.scripts.seed_exercise_library`, then Uvicorn on `$PORT` (Render **free** tier does not support `preDeployCommand`, so migrations and seeding run on each start — safe because both are idempotent). If the seed files are invalid the start command fails and Render keeps serving the previous deploy.
4. Smoke test: open `https://<your-service>.onrender.com/docs` and run signup / plan generate.

**SQLite stays local:** production uses only the Render **Environment** tab — your machine keeps `.env` with SQLite.

## API docs (local)

- Swagger UI: `http://127.0.0.1:8000/docs`

## Test

- `python3 -m pytest -q`

## Exercise library

The plan generator chooses from a curated library (`app/data/exercise_library/exercises_v1.json`, ~230 exercises) rather than letting a model invent exercises. Design: `docs/architecture/plan-generation-pipeline.md`.

- **Source and licence.** Exercise *facts* (names, muscles, difficulty level, equipment) come from [free-exercise-db](https://github.com/yuhonas/free-exercise-db) (Unlicense / public domain), pinned to one commit recorded in the JSON. Its instruction text and images are **not** used. Gaps in the source (carries, dumbbell hinges, bodyweight pulls, ...) are filled with in-house entries marked `source.kind = "in_house"`.
- **Contraindication tags, impact level, goal tags and default tempo are derived by rule** (`app/services/exercise_library/tagging.py`), not judged one exercise at a time. They are conservative heuristics and have **not been reviewed by a coach or physical therapist**.
- **Never hand-edit the generated JSON.** Edit the curation table (`app/scripts/exercise_curation.py`) or a rule, then rebuild: `python3 -m app.scripts.build_exercise_library` (downloads the pinned snapshot). A test fails if the committed JSON drifts from the rules.
- **Removing an exercise** from the JSON deactivates it on the next seed instead of deleting it, so historic plans keep resolving.
- **Known coverage gaps** (no equipment-free carries, bodyweight vertical pulls or upper-body isolation, and only advanced bodyweight vertical pushes) are listed in `tests/test_exercise_seed.py::KNOWN_COVERAGE_GAPS`; a test fails once one is filled so the entry gets removed.
