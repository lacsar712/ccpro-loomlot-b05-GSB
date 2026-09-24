from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DyeHouseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    water_hardness_mg_l: int = Field(..., ge=0, le=500, alias="waterHardnessMgL")
    water_reused: bool = Field(..., alias="waterReused")
    water_note: Optional[str] = Field(None, max_length=255, alias="waterNote")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class DyeHouseUpdate(BaseModel):
    # 硬度与是否回用水为水源核心字段：更新时必须随表单一并补齐，缺一即 400
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    water_hardness_mg_l: Optional[int] = Field(None, ge=0, le=500, alias="waterHardnessMgL")
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
