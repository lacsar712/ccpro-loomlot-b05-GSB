from typing import List, TYPE_CHECKING

from sqlalchemy import String, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.vat import Vat


class DyeHouse(Base):
    __tablename__ = "dye_houses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 水源硬度，单位 mg/L(CaCO3)，0–500；> 200 时限单坊染程布重 ≤ 30kg
    water_hardness_mg_l: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 是否使用回用水；为真时该坊染缸纤维不得含“棉”
    water_reused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 原自由文本用水说明，降级为可选备注
    water_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    vats: Mapped[List["Vat"]] = relationship(
        "Vat", back_populates="dye_house", cascade="all, delete-orphan"
    )
