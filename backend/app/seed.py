from datetime import datetime, timedelta, timezone

from app.auth import hash_password
from app.database import SessionLocal
from app.models.dye_house import DyeHouse
from app.models.dye_lot import DyeLot
from app.models.fastness_check import FastnessCheck
from app.models.user import User
from app.models.vat import Vat


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all(
                [
                    User(
                        username="admin",
                        hashed_password=hash_password("123456"),
                        role="admin",
                        display_name="染坊主管",
                    ),
                    User(
                        username="dyer",
                        hashed_password=hash_password("123456"),
                        role="dyer",
                        display_name="染程操作员",
                    ),
                ]
            )
            db.commit()

        if db.query(DyeHouse).count() == 0:
            h1 = DyeHouse(
                name="蓝靛一号坊",
                water_hardness_mg_l=80,
                water_reused=False,
                water_note="软化井水，硬度约 80mg/L，低于 200 阈值，布重不受限",
                notes="主做棉麻靛蓝与草木染",
            )
            h2 = DyeHouse(
                name="青石二号坊",
                water_hardness_mg_l=120,
                water_reused=False,
                water_note="河溪砂滤水，硬度约 120mg/L，日供约 12 吨",
                notes="专职丝绢与混纺缸染",
            )
            # 高硬度且回用水：硬度 >200mg/L 时限单缸布重 30kg；回用水坊禁含「棉」纤维
            h3 = DyeHouse(
                name="硬水回用三号坊",
                water_hardness_mg_l=260,
                water_reused=True,
                water_note="回用水，硬度 260mg/L（>200）：染程布重限 30kg；回用水纤维禁含「棉」",
                notes="高硬度回用水示范坊，仅做麻与化纤",
            )
            db.add_all([h1, h2, h3])
            db.flush()

            v1 = Vat(
                dye_house_id=h1.id,
                vat_code="V-01",
                fiber_type="棉",
                capacity_l=800.0,
                status="dyeing",
            )
            v2 = Vat(
                dye_house_id=h1.id,
                vat_code="V-02",
                fiber_type="麻",
                capacity_l=600.0,
                status="ready",
            )
            v3 = Vat(
                dye_house_id=h2.id,
                vat_code="S-01",
                fiber_type="丝",
                capacity_l=350.0,
                status="ready",
            )
            v4 = Vat(
                dye_house_id=h2.id,
                vat_code="S-02",
                fiber_type="混纺",
                capacity_l=500.0,
                status="drain",
            )
            # 回用水坊不可含棉，用麻；高硬度坊布重须 <=30kg
            v5 = Vat(
                dye_house_id=h3.id,
                vat_code="R-01",
                fiber_type="麻",
                capacity_l=450.0,
                status="dyeing",
            )
            db.add_all([v1, v2, v3, v4, v5])
            db.flush()

            now = datetime.now(timezone.utc)
            lot1 = DyeLot(
                vat_id=v1.id,
                recipe_name="靛蓝冷染三浸",
                fabric_kg=42.5,
                started_at=now - timedelta(hours=6),
                operator_name="染程操作员",
            )
            lot2 = DyeLot(
                vat_id=v3.id,
                recipe_name="青蓝套染",
                fabric_kg=18.0,
                started_at=now - timedelta(days=2),
                operator_name="染坊主管",
            )
            # 高硬度回用水坊的进行中染程：布重 25kg <= 30kg 上限
            lot3 = DyeLot(
                vat_id=v5.id,
                recipe_name="厚麻深缸",
                fabric_kg=25.0,
                started_at=now - timedelta(hours=2),
                operator_name="染程操作员",
            )
            db.add_all([lot1, lot2, lot3])
            db.flush()

            # lot2 was on ready vat historically — keep v3 ready for demo create path
            # Re-set: creating lot2 would have set dyeing; for seed we leave one dyeing + one ready
            v3.status = "ready"
            db.add_all(
                [
                    FastnessCheck(
                        dye_lot_id=lot1.id,
                        checked_at=now - timedelta(hours=1),
                        wash_fastness=4,
                        rub_fastness=3.5,
                        temp_c=40.0,
                        notes="湿摩略偏，可出货",
                    ),
                    FastnessCheck(
                        dye_lot_id=lot2.id,
                        checked_at=now - timedelta(days=1),
                        wash_fastness=5,
                        rub_fastness=4.0,
                        temp_c=37.0,
                        notes=None,
                    ),
                ]
            )
            db.commit()
            print("Seed data inserted.")
        else:
            print("Seed skipped (data exists).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
