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
from app.water_rules import enforce_fabric_kg

router = APIRouter(prefix="/api/dye-lots", tags=["dye-lots"])

ALLOWED_VAT_STATUSES = {"ready", "dyeing"}


def _get_vat_or_400(db: Session, vat_id: int, *, moved: bool = False) -> Vat:
    vat = db.query(Vat).filter(Vat.id == vat_id).first()
    if not vat:
        raise HTTPException(status_code=400, detail="染缸不存在")
    if vat.status not in ALLOWED_VAT_STATUSES:
        if moved:
            raise HTTPException(
                status_code=409,
                detail=f"目标染缸状态为「{vat.status}」，无法改挂染程",
            )
        raise HTTPException(
            status_code=409,
            detail=f"染缸状态为「{vat.status}」，仅 ready 或 dyeing 时可新建染程",
        )
    return vat


def _get_house_or_400(db: Session, dye_house_id: int) -> DyeHouse:
    house = db.query(DyeHouse).filter(DyeHouse.id == dye_house_id).first()
    if not house:
        # 染缸必有所属染坊；走到这里说明数据异常
        raise HTTPException(status_code=400, detail="染坊不存在")
    return house


@router.get("", response_model=List[DyeLotOut])
def list_dye_lots(
    vat_id: Optional[int] = Query(None, alias="vatId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(DyeLot)
    if vat_id is not None:
        q = q.filter(DyeLot.vat_id == vat_id)
    return q.order_by(DyeLot.id.desc()).all()


@router.post("", response_model=DyeLotOut, status_code=status.HTTP_201_CREATED)
def create_dye_lot(
    payload: DyeLotCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    vat = _get_vat_or_400(db, payload.vat_id)
    house = _get_house_or_400(db, vat.dye_house_id)
    # 水源硬度联锁：高硬度坊布重 ≤ 30kg（与染缸路由共用同一判定）
    enforce_fabric_kg(house.water_hardness_mg_l, payload.fabric_kg)
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
        target_vat = _get_vat_or_400(db, data["vat_id"], moved=True)
    effective_vat = target_vat or db.query(Vat).filter(Vat.id == item.vat_id).first()
    house = _get_house_or_400(db, effective_vat.dye_house_id)

    # 以提交后的最终布重再过一遍同一套水源硬度判定（换缸到高硬坊同样受限）
    effective_fabric_kg = (
        data["fabric_kg"] if "fabric_kg" in data else item.fabric_kg
    )
    enforce_fabric_kg(house.water_hardness_mg_l, effective_fabric_kg)

    if target_vat is not None:
        target_vat.status = "dyeing"
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
