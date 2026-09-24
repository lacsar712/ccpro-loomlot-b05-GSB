"""轻量幂等迁移：无 Alembic 场景下为既有库补齐新列。

染坊水源由自由文本拆为「硬度 mg/L」与「是否回用水」两项：
- water_hardness_mg_l: INTEGER NOT NULL（既有行回填 0）
- water_reused: BOOLEAN NOT NULL（既有行回填 false）
- water_note: 由 NOT NULL 放宽为可空（降级为可选备注）

PostgreSQL 支持 ADD COLUMN IF NOT EXISTS；其它方言（如测试用 sqlite）
直接依赖 create_all 建表，不在此处理。
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine

_STATEMENTS = [
    "ALTER TABLE dye_houses ADD COLUMN IF NOT EXISTS water_hardness_mg_l INTEGER",
    "UPDATE dye_houses SET water_hardness_mg_l = 0 WHERE water_hardness_mg_l IS NULL",
    "ALTER TABLE dye_houses ALTER COLUMN water_hardness_mg_l SET NOT NULL",
    "ALTER TABLE dye_houses ADD COLUMN IF NOT EXISTS water_reused BOOLEAN",
    "UPDATE dye_houses SET water_reused = false WHERE water_reused IS NULL",
    "ALTER TABLE dye_houses ALTER COLUMN water_reused SET NOT NULL",
    "ALTER TABLE dye_houses ALTER COLUMN water_note DROP NOT NULL",
]


def run_lightweight_migrations(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        for stmt in _STATEMENTS:
            conn.execute(text(stmt))
