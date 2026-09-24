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
from app.water_rules import HARDNESS_HIGH_THRESHOLD

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    # 回用水坊数：与 GET /api/dye-houses?reusedOnly=true 的筛行同条件、同计数
    reused_house_count = (
        db.query(func.count(DyeHouse.id))
        .filter(DyeHouse.water_reused.is_(True))
        .scalar()
        or 0
    )
    # 因硬度受限的进行中染程数：染程经染缸 join 染坊，取染色中(dyeing)缸
    # 且坊内硬度 > 200 的染程手数；与染程列表按同一条件过滤的行数一致
    hardness_restricted_active_lot_count = (
        db.query(func.count(DyeLot.id))
        .join(Vat, DyeLot.vat_id == Vat.id)
        .join(DyeHouse, Vat.dye_house_id == DyeHouse.id)
        .filter(Vat.status == "dyeing", DyeHouse.water_hardness_mg_l > HARDNESS_HIGH_THRESHOLD)
        .scalar()
        or 0
    )
    return DashboardStats(
        dye_house_total=db.query(func.count(DyeHouse.id)).scalar() or 0,
        reused_house_count=reused_house_count,
        hardness_restricted_active_lot_count=hardness_restricted_active_lot_count,
        vat_ready_count=db.query(func.count(Vat.id)).filter(Vat.status == "ready").scalar() or 0,
        vat_dyeing_count=db.query(func.count(Vat.id)).filter(Vat.status == "dyeing").scalar() or 0,
        lots_last_7d=(
            db.query(func.count(DyeLot.id))
            .filter(DyeLot.started_at >= now - timedelta(days=7))
            .scalar()
            or 0
        ),
        checks_last_24h=(
            db.query(func.count(FastnessCheck.id))
            .filter(FastnessCheck.checked_at >= now - timedelta(hours=24))
            .scalar()
            or 0
        ),
    )
