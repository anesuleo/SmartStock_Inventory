from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base
from fastapi import FastAPI, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import date

from .database import get_db, engine
from .models import Base, InventoryDB, StockMovementDB
from .schemas import InventoryCreate, InventoryRead, InventoryPatch, StockMovementCreate, StockMovementRead

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

# Define FastAPI app
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- CRUD Methods ----------
@app.post("/api/inventory", response_model=InventoryRead, status_code=201)
def create_inventory(item: InventoryCreate, db: Session = Depends(get_db)):
    record = InventoryDB(**item.model_dump())
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Inventory item already exists")

    # log initial stock as an IN movement
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
    stmt = select(InventoryDB).order_by(InventoryDB.id).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()


@app.get("/api/inventory/{item_id}", response_model=InventoryRead)
def get_inventory_item(item_id: int, db: Session = Depends(get_db)):
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
    return record


@app.put("/api/inventory/{item_id}", response_model=InventoryRead, status_code=202)
def update_inventory(item_id: int, payload: InventoryCreate, db: Session = Depends(get_db)):
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
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(record)
    db.commit()
    return None

@app.post("/api/inventory/scan", response_model=InventoryRead)
async def scan_barcode(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    barcode = payload.get("barcode")
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode not provided")

    item = db.query(InventoryDB).filter(InventoryDB.barcode == barcode).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return item

@app.post("/api/inventory/{item_id}/movement", response_model=StockMovementRead, status_code=201)
def add_movement(item_id: int, payload: StockMovementCreate, db: Session = Depends(get_db)):
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
    else:
        raise HTTPException(status_code=400, detail="movement_type must be IN or OUT")

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
    stmt = (
        select(StockMovementDB)
        .where(StockMovementDB.movement_type == "OUT")
        .order_by(StockMovementDB.movement_date.desc(), StockMovementDB.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.execute(stmt).scalars().all()

@app.get("/api/movements", response_model=list[StockMovementRead])
def list_movements(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    stmt = (
        select(StockMovementDB)
        .order_by(StockMovementDB.movement_date.desc(), StockMovementDB.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.execute(stmt).scalars().all()