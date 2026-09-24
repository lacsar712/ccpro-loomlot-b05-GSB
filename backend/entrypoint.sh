#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for i in range(60):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as e:
        print(f"DB not ready ({i+1}/60): {e}")
        time.sleep(2)
else:
    raise SystemExit("Database not ready after retries")
PY

echo "Creating tables..."
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"

echo "Migrating legacy schema (water source split)..."
python - <<'PY'
from sqlalchemy import text
from app.database import engine

with engine.begin() as conn:
    cols = {
        r[0]
        for r in conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='dye_houses'"
            )
        )
    }
    if "water_hardness_mg_l" not in cols:
        conn.execute(
            text(
                "ALTER TABLE dye_houses "
                "ADD COLUMN water_hardness_mg_l INTEGER NOT NULL DEFAULT 80"
            )
        )
        print("Added dye_houses.water_hardness_mg_l (default 80).")
    if "water_reused" not in cols:
        conn.execute(
            text(
                "ALTER TABLE dye_houses ADD COLUMN water_reused BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        print("Added dye_houses.water_reused (default false).")
    # water_note 由必填自由文本改为可选备注
    conn.execute(text("ALTER TABLE dye_houses ALTER COLUMN water_note DROP NOT NULL"))
print("Schema migration check done.")
PY

echo "Seeding data..."
python -c "from app.seed import seed; seed()"

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8600
