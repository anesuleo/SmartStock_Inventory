from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .database import get_db, engine
from .models import Base, InventoryDB, StockMovementDB
from .schemas import (
    InventoryCreate, InventoryRead, InventoryPatch,
    StockMovementCreate, StockMovementRead,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on startup if they don't exist
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

# Allow requests from the GUI running on a different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Simple health check to confirm the service is running."""
    return {"status": "ok"}


# ── Inventory CRUD ─────────────────────────────────────────────────────────────

@app.post("/api/inventory", response_model=InventoryRead, status_code=201)
def create_inventory(item: InventoryCreate, db: Session = Depends(get_db)):
    """
    Create a new inventory item.
    Also logs the initial stock quantity as an IN movement.
    Returns 409 if an item with the same barcode already exists.
    """
    record = InventoryDB(**item.model_dump())
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Inventory item already exists")

    # Log the initial stock as an IN movement so history is complete from day one
    movement = StockMovementDB(
        inventory_id=record.id,
        movement_type="IN",
        quantity=record.stock_quantity,
        movement_date=record.stocked_date,
    )
    db.add(movement)
    db.commit()
    return record


@app.get("/api/inventory", response_model=list[InventoryRead])
def list_inventory(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Return a paginated list of all inventory items."""
    stmt = select(InventoryDB).order_by(InventoryDB.id).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()


# ── IMPORTANT: /scan must be defined BEFORE /{item_id} ───────────────────────
# FastAPI matches routes in order. If /{item_id} comes first, the string "scan"
# gets matched as an item_id and causes a 422 validation error.

@app.post("/api/inventory/scan", response_model=InventoryRead)
async def scan_barcode(request: Request, db: Session = Depends(get_db)):
    """
    Look up an inventory item by barcode.
    Used by the barcode scanner to identify items quickly.
    Returns 400 if no barcode is provided, 404 if not found.
    """
    payload = await request.json()
    barcode = payload.get("barcode")
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode not provided")

    item = db.query(InventoryDB).filter(InventoryDB.barcode == barcode).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/api/inventory/{item_id}", response_model=InventoryRead)
def get_inventory_item(item_id: int, db: Session = Depends(get_db)):
    """Fetch a single inventory item by ID. Returns 404 if not found."""
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
    return record


@app.put("/api/inventory/{item_id}", response_model=InventoryRead, status_code=202)
def update_inventory(item_id: int, payload: InventoryCreate, db: Session = Depends(get_db)):
    """
    Fully replace an inventory item with new data.
    Returns 404 if not found, 409 if the update causes a barcode conflict.
    """
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in payload.model_dump().items():
        setattr(record, key, value)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Failed to update item")
    return record


@app.patch("/api/inventory/{item_id}", response_model=InventoryRead, status_code=202)
def patch_inventory(item_id: int, payload: InventoryPatch, db: Session = Depends(get_db)):
    """
    Partially update an inventory item — only the supplied fields are changed.
    Returns 404 if not found, 409 if the update causes a barcode conflict.
    """
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Failed to update item")
    return record


@app.delete("/api/inventory/{item_id}", status_code=204)
def delete_inventory(item_id: int, db: Session = Depends(get_db)):
    """Delete an inventory item and all its movements. Returns 404 if not found."""
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(record)
    db.commit()


# ── Stock movements ────────────────────────────────────────────────────────────

@app.post("/api/inventory/{item_id}/movement", response_model=StockMovementRead, status_code=201)
def add_movement(item_id: int, payload: StockMovementCreate, db: Session = Depends(get_db)):
    """
    Record a stock movement (IN or OUT) for an inventory item.
    IN movements increase stock, OUT movements decrease it.
    Returns 400 if there is not enough stock for an OUT movement.
    """
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")

    mdate = payload.movement_date or date.today()

    if payload.movement_type == "IN":
        record.stock_quantity += payload.quantity
    elif payload.movement_type == "OUT":
        if record.stock_quantity < payload.quantity:
            raise HTTPException(status_code=400, detail="Not enough stock")
        record.stock_quantity -= payload.quantity

    movement = StockMovementDB(
        inventory_id=item_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        movement_date=mdate,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@app.get("/api/sales", response_model=list[StockMovementRead])
def list_sales(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    """Return all OUT movements (sales/usage), most recent first."""
    stmt = (
        select(StockMovementDB)
        .where(StockMovementDB.movement_type == "OUT")
        .order_by(StockMovementDB.movement_date.desc(), StockMovementDB.id.desc())
        .limit(limit).offset(offset)
    )
    return db.execute(stmt).scalars().all()


@app.get("/api/movements", response_model=list[StockMovementRead])
def list_movements(
    item_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Return stock movements, most recent first.
    Optionally filter by item_id using ?item_id=<id>.
    """
    stmt = select(StockMovementDB)

    # Filter by item if provided — avoids fetching all movements unnecessarily
    if item_id is not None:
        stmt = stmt.where(StockMovementDB.inventory_id == item_id)

    stmt = stmt.order_by(
        StockMovementDB.movement_date.desc(),
        StockMovementDB.id.desc()
    ).limit(limit).offset(offset)

    return db.execute(stmt).scalars().all()