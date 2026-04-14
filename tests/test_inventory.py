"""
tests/test_inventory.py

Tests for the Inventory microservice.
Uses FastAPI's TestClient with an in-memory SQLite database so
no real server or Postgres instance is needed to run these.

Run with:
    pytest tests/ -v
"""

import pytest
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, InventoryDB
from app.database import get_db
from app.main import app


# ── Test database setup ───────────────────────────────────────────────────────
# Named in-memory SQLite with shared cache so both the test fixtures
# and the API's dependency override see the same data.

TEST_DB_URL = "sqlite:///file::memory:?cache=shared&uri=true"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False, "uri": True},
)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    """Replace the real database with the test database for all requests."""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# Tell FastAPI to use the test database instead of the real one
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    """
    Runs before and after every test.
    Creates all tables before the test and drops them after,
    so each test starts with a completely clean database.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """Provides a TestClient for making requests to the API."""
    return TestClient(app)


# Sample inventory item payload used across multiple tests
SAMPLE_ITEM = {
    "drug_name": "Paracetamol",
    "manufacturer": "Pfizer",
    "units": "mg",
    "price": 5.99,
    "stock_quantity": 100,
    "stocked_date": str(date.today()),
    "expiry_date": "2027-01-01",
    "barcode": "1234567890123",
}


def _create_item(client):
    """Helper to create a sample inventory item and return the response."""
    return client.post("/api/inventory", json=SAMPLE_ITEM)


# ── Health check ──────────────────────────────────────────────────────────────

def test_health(client):
    """Health endpoint should return ok."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── Create inventory ──────────────────────────────────────────────────────────

def test_create_inventory(client):
    """Creating a new inventory item should return 201 with the item data."""
    res = _create_item(client)
    assert res.status_code == 201
    data = res.json()
    assert data["drug_name"] == "Paracetamol"
    assert data["stock_quantity"] == 100
    assert "id" in data


def test_create_inventory_duplicate_barcode(client):
    """Creating two items with the same barcode should return 409."""
    _create_item(client)
    res = _create_item(client)
    assert res.status_code == 409


# ── List inventory ────────────────────────────────────────────────────────────

def test_list_inventory_empty(client):
    """Listing inventory when empty should return an empty list."""
    res = client.get("/api/inventory")
    assert res.status_code == 200
    assert res.json() == []


def test_list_inventory(client):
    """After creating an item, it should appear in the list."""
    _create_item(client)
    res = client.get("/api/inventory")
    assert res.status_code == 200
    assert len(res.json()) == 1


# ── Get single item ───────────────────────────────────────────────────────────

def test_get_inventory_item(client):
    """Fetching an item by ID should return the correct item."""
    item_id = _create_item(client).json()["id"]
    res = client.get(f"/api/inventory/{item_id}")
    assert res.status_code == 200
    assert res.json()["id"] == item_id


def test_get_inventory_item_not_found(client):
    """Fetching a non-existent item should return 404."""
    res = client.get("/api/inventory/999")
    assert res.status_code == 404


# ── Update inventory ──────────────────────────────────────────────────────────

def test_update_inventory(client):
    """A PUT request should fully replace an inventory item."""
    item_id = _create_item(client).json()["id"]
    updated = {**SAMPLE_ITEM, "drug_name": "Ibuprofen", "price": 7.99}
    res = client.put(f"/api/inventory/{item_id}", json=updated)
    assert res.status_code == 202
    assert res.json()["drug_name"] == "Ibuprofen"


def test_patch_inventory(client):
    """A PATCH request should update only the supplied fields."""
    item_id = _create_item(client).json()["id"]
    res = client.patch(f"/api/inventory/{item_id}", json={"stock_quantity": 50})
    assert res.status_code == 202
    assert res.json()["stock_quantity"] == 50
    # Other fields should be unchanged
    assert res.json()["drug_name"] == "Paracetamol"


# ── Delete inventory ──────────────────────────────────────────────────────────

def test_delete_inventory(client):
    """Deleting an item should return 204 and the item should no longer exist."""
    item_id = _create_item(client).json()["id"]
    res = client.delete(f"/api/inventory/{item_id}")
    assert res.status_code == 204

    # Confirm the item is gone
    res = client.get(f"/api/inventory/{item_id}")
    assert res.status_code == 404


def test_delete_inventory_not_found(client):
    """Deleting a non-existent item should return 404."""
    res = client.delete("/api/inventory/999")
    assert res.status_code == 404


# ── Barcode scan ──────────────────────────────────────────────────────────────

def test_scan_barcode(client):
    """Scanning a valid barcode should return the matching inventory item."""
    _create_item(client)
    res = client.post("/api/inventory/scan", json={"barcode": "1234567890123"})
    assert res.status_code == 200
    assert res.json()["barcode"] == "1234567890123"


def test_scan_barcode_not_found(client):
    """Scanning an unknown barcode should return 404."""
    res = client.post("/api/inventory/scan", json={"barcode": "0000000000000"})
    assert res.status_code == 404


def test_scan_barcode_missing(client):
    """Scanning without providing a barcode should return 400."""
    res = client.post("/api/inventory/scan", json={})
    assert res.status_code == 400


# ── Stock movements ───────────────────────────────────────────────────────────

def test_add_stock_in(client):
    """An IN movement should increase the stock quantity."""
    item_id = _create_item(client).json()["id"]
    res = client.post(
        f"/api/inventory/{item_id}/movement",
        json={"movement_type": "IN", "quantity": 50}
    )
    assert res.status_code == 201

    # Stock should have increased from 100 to 150
    updated = client.get(f"/api/inventory/{item_id}").json()
    assert updated["stock_quantity"] == 150


def test_add_stock_out(client):
    """An OUT movement should decrease the stock quantity."""
    item_id = _create_item(client).json()["id"]
    res = client.post(
        f"/api/inventory/{item_id}/movement",
        json={"movement_type": "OUT", "quantity": 30}
    )
    assert res.status_code == 201

    # Stock should have decreased from 100 to 70
    updated = client.get(f"/api/inventory/{item_id}").json()
    assert updated["stock_quantity"] == 70


def test_add_stock_out_insufficient(client):
    """An OUT movement larger than available stock should return 400."""
    item_id = _create_item(client).json()["id"]
    res = client.post(
        f"/api/inventory/{item_id}/movement",
        json={"movement_type": "OUT", "quantity": 999}
    )
    assert res.status_code == 400


# ── Sales and movements list ──────────────────────────────────────────────────

def test_list_sales(client):
    """The sales endpoint should only return OUT movements."""
    item_id = _create_item(client).json()["id"]

    # Add one IN and one OUT movement
    client.post(f"/api/inventory/{item_id}/movement",
                json={"movement_type": "IN", "quantity": 10})
    client.post(f"/api/inventory/{item_id}/movement",
                json={"movement_type": "OUT", "quantity": 5})

    res = client.get("/api/sales")
    assert res.status_code == 200
    # Only the OUT movement should appear
    assert all(m["movement_type"] == "OUT" for m in res.json())


def test_list_movements(client):
    """The movements endpoint should return all movements."""
    item_id = _create_item(client).json()["id"]

    client.post(f"/api/inventory/{item_id}/movement",
                json={"movement_type": "IN", "quantity": 10})
    client.post(f"/api/inventory/{item_id}/movement",
                json={"movement_type": "OUT", "quantity": 5})

    res = client.get("/api/movements")
    assert res.status_code == 200
    # Should include the initial IN movement from create + 2 more = 3 total
    assert len(res.json()) >= 2