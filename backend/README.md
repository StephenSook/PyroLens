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

## Seed Demo Data

Populate Supabase with dashboard-friendly sample burns, one net-positive metric row, and a colocated sensor node plus reading:

```bash
.venv/bin/python scripts/seed_demo_data.py
```

Optional flags:

- `--device-id` to match your ESP bridge device ID
- `--site-name` to label the seeded sensor node
- `--lat` / `--lon` to place the demo site where your dashboard expects it
- `--county` to control the seeded burn county name

## Import Burn History

Import a GeoJSON `FeatureCollection` into the `burns` table:

```bash
.venv/bin/python scripts/import_burns_geojson.py path/to/burns.geojson
```

Each feature must include:

- `properties.county`
- `properties.burn_date` as `YYYY-MM-DD`
- `properties.acreage`
- `properties.objective`
- `properties.outcome`
- `geometry`

Optional net-positive metrics can be supplied either as flat properties or as a nested `properties.net_positive_metrics` object with:

- `co2_prevented`
- `prescribed_emissions`
- `wildfire_baseline_emissions`
- `biodiversity_gain_index`
- `fuel_load_reduction_pct`
- `vegetation_recovery_curve`

## Live ESP Sensor Setup

To make live bridge readings count as "nearby" sensor data, provision the sensor node once with real coordinates:

```bash
.venv/bin/python scripts/provision_sensor_node.py --device-id serial-bridge-esp32 --site-name "Georgia Pilot Burn Site" --lat 33.749 --lon -84.388
```

Then run the serial bridge with the same `SENSOR_DEVICE_ID`:

```bash
SENSOR_DEVICE_ID=serial-bridge-esp32 .venv/bin/python serial_bridge.py
```

If you use a different `device_id`, pass it to both the provisioning script and the bridge command.
