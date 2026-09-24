from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# 水源硬度允许范围与高硬度阈值，详见 app/water_rules.py
HARDNESS_MIN = 0
HARDNESS_MAX = 500


class DyeHouseCreate(BaseModel):
    # 硬度与是否回用水为必填；置为 Optional 以便路由对缺字段返回中文 400。
    name: str = Field(..., min_length=1, max_length=128)
    water_hardness_mg_l: Optional[int] = Field(
        None, ge=HARDNESS_MIN, le=HARDNESS_MAX, alias="waterHardnessMgL"
    )
    water_reused: Optional[bool] = Field(None, alias="waterReused")
    water_note: Optional[str] = Field(None, max_length=255, alias="waterNote")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class DyeHouseUpdate(BaseModel):
    # 字段本身可选以支持局部提交，但更新染坊时硬度与是否回用水必须随请求补齐，
    # 缺失由路由返回 400 中文提示（见 routers/dye_houses.py）。
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    water_hardness_mg_l: Optional[int] = Field(
        None, ge=HARDNESS_MIN, le=HARDNESS_MAX, alias="waterHardnessMgL"
    )
    water_reused: Optional[bool] = Field(None, alias="waterReused")
    water_note: Optional[str] = Field(None, max_length=255, alias="waterNote")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class DyeHouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    water_hardness_mg_l: int = Field(serialization_alias="waterHardnessMgL")
    water_reused: bool = Field(serialization_alias="waterReused")
    water_note: Optional[str] = Field(None, serialization_alias="waterNote")
    notes: Optional[str] = None
