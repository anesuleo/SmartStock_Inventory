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
from .models import Base, InventoryDB, SaleDB
from .schemas import InventoryCreate, InventoryRead, InventoryPatch, SaleCreate, SaleRead

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

@app.post("/api/inventory/{item_id}/sell", response_model=SaleRead, status_code=201)
def sell_inventory(item_id: int, payload: SaleCreate, db: Session = Depends(get_db)):
    record = db.get(InventoryDB, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")

    if record.stock_quantity < payload.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    record.stock_quantity -= payload.quantity

    sale = SaleDB(
        inventory_id=item_id,
        quantity=payload.quantity,
        sold_date=payload.sold_date or date.today()
    )

    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale