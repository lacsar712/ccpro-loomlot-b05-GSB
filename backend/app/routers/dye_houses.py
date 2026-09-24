from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.dye_house import DyeHouse
from app.models.user import User
from app.schemas.dye_house import DyeHouseCreate, DyeHouseUpdate, DyeHouseOut

router = APIRouter(prefix="/api/dye-houses", tags=["dye-houses"])


def _require_water_fields(data: dict, *, partial: bool) -> None:
    """硬度与是否回用水必填：新建缺失或更新漏带均返回中文 400。"""
    missing = []
    if "water_hardness_mg_l" not in data or data["water_hardness_mg_l"] is None:
        missing.append("水源硬度（mg/L）")
    if "water_reused" not in data or data["water_reused"] is None:
        missing.append("是否回用水")
    if missing:
        when = "更新染坊" if partial else "新建染坊"
        raise HTTPException(
            status_code=400,
            detail=f"{when}必须填写{'、'.join(missing)}，请补齐后再提交",
        )


@router.get("", response_model=List[DyeHouseOut])
def list_dye_houses(
    reused_only: Optional[bool] = Query(None, alias="reusedOnly"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(DyeHouse)
    if reused_only is not None:
        q = q.filter(DyeHouse.water_reused.is_(reused_only))
    return q.order_by(DyeHouse.id).all()


@router.post("", response_model=DyeHouseOut, status_code=status.HTTP_201_CREATED)
def create_dye_house(
    payload: DyeHouseCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    _require_water_fields(data, partial=False)
    item = DyeHouse(
        name=payload.name,
        water_hardness_mg_l=payload.water_hardness_mg_l,
        water_reused=payload.water_reused,
        water_note=payload.water_note,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{house_id}", response_model=DyeHouseOut)
def get_dye_house(
    house_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeHouse).filter(DyeHouse.id == house_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染坊不存在")
    return item


@router.put("/{house_id}", response_model=DyeHouseOut)
def update_dye_house(
    house_id: int,
    payload: DyeHouseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeHouse).filter(DyeHouse.id == house_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染坊不存在")
    data = payload.model_dump(exclude_unset=True)
    # 更新请求必须先补齐水源两字段，避免把旧的自由文本记录带进新规则。
    _require_water_fields(data, partial=True)
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{house_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dye_house(
    house_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeHouse).filter(DyeHouse.id == house_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染坊不存在")
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="该染坊仍有关联记录，无法删除")
