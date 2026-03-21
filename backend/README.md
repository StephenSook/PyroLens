# PyroLens FastAPI Backend

## Requirements

- Python 3.10+
- pip

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

## Supabase Postgres

To use Supabase as the backend database, set `DATABASE_URL` in `backend/.env` to your Supabase Postgres connection string.

Recommended options:

- Persistent backend service on a normal VM/container:

```bash
DATABASE_URL=postgresql+psycopg2://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

- Supabase pooler in transaction mode:

```bash
DATABASE_URL=postgresql+psycopg2://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

Notes:

- PyroLens will automatically append `sslmode=require` for Supabase URLs if it is missing.
- PyroLens will automatically disable SQLAlchemy pooling for Supabase transaction-pooler URLs on port `6543`.
- You can force either behavior with `DATABASE_SSLMODE` and `DATABASE_DISABLE_POOLING` in `backend/.env`.

## Alembic Migrations

Create a migration:

```bash
alembic revision --autogenerate -m "init"
```

Apply migrations:

```bash
alembic upgrade head
```
