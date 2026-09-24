"""染坊水源 → 染程布重 / 染缸纤维 的统一联锁判定。

染程路由（app/routers/dye_lots.py）与染缸路由（app/routers/vats.py）
必须调用本模块的同一套函数，避免两处规则漂移：

- 水源硬度 > HARDNESS_HIGH_THRESHOLD(200 mg/L) 的染坊，其缸上新建或
  更新染程的布重不得超过 MAX_FABRIC_KG_HIGH_HARDNESS(30 kg)，超限 400，
  且错误信息须点明因硬度过高。
- 使用回用水（water_reused=True）的染坊，其染缸新建或改缸的纤维类型
  不得含「棉」字样，违者 409。
"""
from fastapi import HTTPException

#: 高硬度阈值（mg/L，以 CaCO3 计），严格大于该值即受限
HARDNESS_HIGH_THRESHOLD = 200
#: 高硬度水源下单染程布重上限（kg）
MAX_FABRIC_KG_HIGH_HARDNESS = 30.0
#: 回用水下禁用的纤维字样
COTTON_KEYWORD = "棉"


def enforce_fabric_kg(hardness_mg_l: int, fabric_kg: float) -> None:
    """硬度超限则布重受限；超限抛 400，信息点明因硬度。"""
    if (
        hardness_mg_l is not None
        and hardness_mg_l > HARDNESS_HIGH_THRESHOLD
        and fabric_kg is not None
        and fabric_kg > MAX_FABRIC_KG_HIGH_HARDNESS
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"该染坊水源硬度 {hardness_mg_l}mg/L 高于 {HARDNESS_HIGH_THRESHOLD}mg/L，"
                f"染程布重不得超过 {MAX_FABRIC_KG_HIGH_HARDNESS:g}kg"
                f"（当前 {fabric_kg:g}kg），请降低布重或改用低硬度水源染坊"
            ),
        )


def enforce_fiber_type(water_reused: bool, fiber_type: str) -> None:
    """回用水坊禁止纤维含「棉」；违者抛 409。"""
    if water_reused and fiber_type is not None and COTTON_KEYWORD in fiber_type:
        raise HTTPException(
            status_code=409,
            detail=(
                f"该染坊使用回用水，染缸纤维不得含「{COTTON_KEYWORD}」字样"
                f"（当前纤维：{fiber_type}）"
            ),
        )
