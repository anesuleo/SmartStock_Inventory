from datetime import date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Date

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

class InventoryDB(Base):
    """
    Represents an inventory record for a pharmaceutical product.
    Each entry corresponds to one batch or product in stock.
    """
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    units: Mapped[str] = mapped_column(String(50), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Dates
    stocked_date: Mapped[date] = mapped_column(Date, nullable=False)   # received/stocked
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Forecasting-critical: when the item was sold (nullable until sold)
    sold_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    barcode: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
