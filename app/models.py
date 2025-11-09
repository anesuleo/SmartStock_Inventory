from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Date

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

#Inventory table
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
    stocked_date: Mapped[str] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[str] = mapped_column(Date, nullable=False)

