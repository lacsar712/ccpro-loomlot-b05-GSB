"""染坊水源规则：硬度与回用水对染程布重、染缸纤维的统一管束。

染程路由（dye_lots）与染缸路由（vats）都必须调用本模块的判定，
看板的受限染程统计复用同一查询条件，保证口径一致。

阈值：
- 水源硬度大于 HARDNESS_LIMIT_MG_L（200 mg/L）的染坊，
  其缸上染程单缸布重不得超过 FABRIC_KG_LIMIT（30 kg）。
- 使用回用水的染坊，其染缸纤维类型不得含「棉」字样。
"""

from fastapi import HTTPException

from app.models.dye_house import DyeHouse
from app.models.dye_lot import DyeLot
from app.models.vat import Vat

HARDNESS_LIMIT_MG_L = 200
FABRIC_KG_LIMIT = 30.0
COTTON_KEYWORD = "棉"


def is_hard_water(house: DyeHouse) -> bool:
    """硬度大于 200 mg/L 即高硬度水。"""
    return house.water_hardness_mg_l > HARDNESS_LIMIT_MG_L


def validate_fabric_kg(house: DyeHouse, fabric_kg: float) -> None:
    """高硬度水染坊的染程布重不得超过 30kg，超限 400 并点明因硬度。"""
    if is_hard_water(house) and fabric_kg > FABRIC_KG_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"染坊「{house.name}」水源硬度 {house.water_hardness_mg_l} mg/L "
                f"高于 {HARDNESS_LIMIT_MG_L} mg/L，染程布重不得超过 {FABRIC_KG_LIMIT:g} kg"
            ),
        )


def validate_fiber_type(house: DyeHouse, fiber_type: str) -> None:
    """回用水染坊的染缸纤维类型不得含「棉」，违者 409。"""
    if house.water_reused and COTTON_KEYWORD in fiber_type:
        raise HTTPException(
            status_code=409,
            detail=(
                f"染坊「{house.name}」使用回用水，染缸纤维不得含「{COTTON_KEYWORD}」字样"
            ),
        )


def hard_water_lot_filters():
    """「因硬度受限的进行中染程」查询条件：

    染程所在染缸的所属染坊硬度 > 200，且染缸仍在染色中（进行中）。
    染程列表与看板统计共用本条件，保证两边手数一致。
    """
    return [
        Vat.id == DyeLot.vat_id,
        DyeHouse.id == Vat.dye_house_id,
        DyeHouse.water_hardness_mg_l > HARDNESS_LIMIT_MG_L,
        Vat.status == "dyeing",
    ]
