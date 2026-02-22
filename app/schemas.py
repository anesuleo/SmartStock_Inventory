from typing import Annotated, Optional, List
from annotated_types import Ge, Le
from pydantic import BaseModel, ConfigDict, StringConstraints, Field
from datetime import date

# ---------- Reusable type aliases ----------
DrugNameStr     = Annotated[str, StringConstraints(min_length=1, max_length=255)]
ManufacturerStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]
UnitStr         = Annotated[str, StringConstraints(min_length=1, max_length=50)]
BarcodeStr = Annotated[str, StringConstraints(min_length=1, max_length=64)]
MovementTypeStr = Annotated[str, StringConstraints(pattern=r"^(IN|OUT)$")]
MovementQtyInt = Annotated[int, Ge(1)]
PriceFloat      = Annotated[float, Ge(0.0)]
StockInt        = Annotated[int, Ge(0)]

# ---------- Inventory ----------
class InventoryCreate(BaseModel):
    drug_name: DrugNameStr
    manufacturer: ManufacturerStr
    units: UnitStr
    price: PriceFloat
    stock_quantity: StockInt
    stocked_date: date
    expiry_date: date
    barcode: BarcodeStr

class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    drug_name: DrugNameStr
    units: UnitStr
    manufacturer: ManufacturerStr
    price: PriceFloat
    stock_quantity: StockInt
    stocked_date: date
    expiry_date: date
    barcode: BarcodeStr

class InventoryPatch(BaseModel):
    drug_name: Optional[DrugNameStr] = None
    manufacturer: Optional[ManufacturerStr] = None
    units: Optional[UnitStr] = None
    price: Optional[PriceFloat] = None
    stock_quantity: Optional[StockInt] = None
    stocked_date: Optional[date] = None
    expiry_date: Optional[date] = None
    barcode: Optional[BarcodeStr] = None

# ---------- Stock Movement ----------
class StockMovementCreate(BaseModel):
    movement_type: MovementTypeStr  # "IN" or "OUT"
    quantity: MovementQtyInt
    movement_date: Optional[date] = None


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inventory_id: int
    movement_type: str
    quantity: int
    movement_date: date