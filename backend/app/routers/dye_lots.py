from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.dye_house import DyeHouse
from app.models.dye_lot import DyeLot
from app.models.user import User
from app.models.vat import Vat
from app.schemas.dye_lot import DyeLotCreate, DyeLotUpdate, DyeLotOut
from app.services import water_rules

router = APIRouter(prefix="/api/dye-lots", tags=["dye-lots"])

ALLOWED_VAT_STATUSES = {"ready", "dyeing"}


@router.get("", response_model=List[DyeLotOut])
def list_dye_lots(
    vat_id: Optional[int] = Query(None, alias="vatId"),
    hardness_limited_active: Optional[bool] = Query(None, alias="hardnessLimitedActive"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(DyeLot)
    if vat_id is not None:
        q = q.filter(DyeLot.vat_id == vat_id)
    if hardness_limited_active is True:
        # 与看板 hardnessLimitedActiveLotCount 同一条件（共享 filter），
        # 看板手数须与本筛选返回的行数一致
        q = (
            q.join(Vat, Vat.id == DyeLot.vat_id)
            .join(DyeHouse, DyeHouse.id == Vat.dye_house_id)
            .filter(*water_rules.hard_water_lot_filters())
        )
    return q.order_by(DyeLot.id.desc()).all()


@router.post("", response_model=DyeLotOut, status_code=status.HTTP_201_CREATED)
def create_dye_lot(
    payload: DyeLotCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    vat = db.query(Vat).filter(Vat.id == payload.vat_id).first()
    if not vat:
        raise HTTPException(status_code=400, detail="染缸不存在")
    if vat.status not in ALLOWED_VAT_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"染缸状态为「{vat.status}」，仅 ready 或 dyeing 时可新建染程",
        )
    house = db.get(DyeHouse, vat.dye_house_id)
    # 高硬度水染坊：染程布重受限（与染缸路由同一套判定）
    water_rules.validate_fabric_kg(house, payload.fabric_kg)
    item = DyeLot(
        vat_id=payload.vat_id,
        recipe_name=payload.recipe_name,
        fabric_kg=payload.fabric_kg,
        started_at=payload.started_at,
        operator_name=payload.operator_name,
    )
    vat.status = "dyeing"
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{lot_id}", response_model=DyeLotOut)
def get_dye_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeLot).filter(DyeLot.id == lot_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染程不存在")
    return item


@router.put("/{lot_id}", response_model=DyeLotOut)
def update_dye_lot(
    lot_id: int,
    payload: DyeLotUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeLot).filter(DyeLot.id == lot_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染程不存在")
    data = payload.model_dump(exclude_unset=True)
    target_vat = None
    if "vat_id" in data and data["vat_id"] != item.vat_id:
        target_vat = db.query(Vat).filter(Vat.id == data["vat_id"]).first()
        if not target_vat:
            raise HTTPException(status_code=400, detail="染缸不存在")
        if target_vat.status not in ALLOWED_VAT_STATUSES:
            raise HTTPException(
                status_code=409,
                detail=f"目标染缸状态为「{target_vat.status}」，无法改挂染程",
            )
        target_vat.status = "dyeing"
    # 改挂看目标缸所属坊，未改挂看原缸所属坊；布重取更新后的最终值
    effective_vat = target_vat or db.get(Vat, item.vat_id)
    house = db.get(DyeHouse, effective_vat.dye_house_id)
    effective_fabric_kg = data.get("fabric_kg", item.fabric_kg)
    # 高硬度水染坊：更新染程布重同样受限（与染缸路由同一套判定）
    water_rules.validate_fabric_kg(house, effective_fabric_kg)
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dye_lot(
    lot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DyeLot).filter(DyeLot.id == lot_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="染程不存在")
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="该染程仍有关联记录，无法删除")
