from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .database import get_db, engine
from .models import Base, InventoryDB
from .schemas import InventoryCreate, InventoryRead, InventoryPatch

# Define FastAPI app
app = FastAPI(title="Inventory Microservice")

# Create all tables and ensures the DB is initialized
Base.metadata.create_all(bind=engine)


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
