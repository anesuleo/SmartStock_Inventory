from datetime import date
from typing import Optional, List

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Date, ForeignKey


class Base(DeclarativeBase):
    pass


class InventoryDB(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    units: Mapped[str] = mapped_column(String(50), nullable=False)

    # Current stock on hand (state)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    stocked_date: Mapped[date] = mapped_column(Date, nullable=False)   # first received/created
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)

    barcode: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # History (ledger)
    movements: Mapped[List["StockMovementDB"]] = relationship(
        back_populates="inventory",
        cascade="all, delete-orphan"
    )


class StockMovementDB(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), nullable=False)

    # IN = received/restock, OUT = sale/usage
    movement_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "IN" or "OUT"

    # store quantity as a positive number (cleaner)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    movement_date: Mapped[date] = mapped_column(Date, nullable=False)

    inventory: Mapped["InventoryDB"] = relationship(back_populates="movements")

    