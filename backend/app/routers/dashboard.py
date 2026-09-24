from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.dye_house import DyeHouse
from app.models.dye_lot import DyeLot
from app.models.fastness_check import FastnessCheck
from app.models.user import User
from app.models.vat import Vat
from app.schemas.dashboard import DashboardStats
from app.services import water_rules

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    # 与染坊列表 reusedOnly=true 同一筛选条件
    reused_water_house_count = (
        db.query(func.count(DyeHouse.id)).filter(DyeHouse.water_reused.is_(True)).scalar() or 0
    )
    # 因硬度受限的进行中染程手数：与染程列表按同一条件（共享 filter）筛出的手数一致
    hardness_limited_active_lot_count = (
        db.query(func.count(DyeLot.id))
        .join(Vat, Vat.id == DyeLot.vat_id)
        .join(DyeHouse, DyeHouse.id == Vat.dye_house_id)
        .filter(*water_rules.hard_water_lot_filters())
        .scalar()
        or 0
    )
    return DashboardStats(
        dye_house_total=db.query(func.count(DyeHouse.id)).scalar() or 0,
        reused_water_house_count=reused_water_house_count,
        vat_ready_count=db.query(func.count(Vat.id)).filter(Vat.status == "ready").scalar() or 0,
        vat_dyeing_count=db.query(func.count(Vat.id)).filter(Vat.status == "dyeing").scalar() or 0,
        lots_last_7d=(
            db.query(func.count(DyeLot.id))
            .filter(DyeLot.started_at >= now - timedelta(days=7))
            .scalar()
            or 0
        ),
        hardness_limited_active_lot_count=hardness_limited_active_lot_count,
        checks_last_24h=(
            db.query(func.count(FastnessCheck.id))
            .filter(FastnessCheck.checked_at >= now - timedelta(hours=24))
            .scalar()
            or 0
        ),
    )
