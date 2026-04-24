import random
from datetime import datetime, timedelta

from database import SessionLocal
from models import InventoryDB, StockMovementDB

# Lists of random data
DRUG_NAMES = [
    "Paracetamol", "Ibuprofen", "Aspirin", "Amoxicillin", "Ciprofloxacin",
    "Vitamin C", "Vitamin D", "Cetirizine", "Loratadine", "Azithromycin",
    "Metformin", "Omeprazole", "Lisinopril", "Amlodipine", "Atorvastatin",
    "Doxycycline", "Hydrocortisone", "Prednisone", "Naproxen", "Insulin",
    "Folic Acid", "Magnesium", "Calcium Tablets", "Zinc Tablets",
    "Cough Syrup", "Antacid", "Antifungal Cream", "Salbutamol",
    "Erythromycin", "Penicillin", "Codeine", "Morphine", "Tramadol",
    "Diclofenac", "Clarithromycin", "Famotidine", "Ranitidine",
    "Levothyroxine", "Warfarin", "Heparin", "Losartan", "Clopidogrel",
    "Simvastatin", "Ketamine", "Diazepam", "Fluoxetine", "Sertraline",
    "Amphotericin B"
]

MANUFACTURERS = [
    "Pfizer", "GSK", "Novartis", "Roche", "AstraZeneca",
    "Johnson & Johnson", "Bayer", "Sanofi", "Merck", "Cipla",
    "Teva Pharma", "Sun Pharma", "Dr. Reddy's", "AbbVie"
]

UNITS = ["mg", "ml", "g", "capsules", "tablets"]


def random_future_date(days_range=730):
    """Generate a random date within the next 2 years."""
    today = datetime.now()
    delta = timedelta(days=random.randint(0, days_range))
    return (today + delta).date()


def generate_movements(db, item: InventoryDB, days: int = 365):
    """
    Generate realistic historical OUT (sales) movements for an item
    going back a given number of days from today, plus occasional
    IN (restock) movements to simulate real pharmacy behaviour.
    """
    today = datetime.now().date()
    start_date = today - timedelta(days=days)

    base_demand = random.randint(1, 15)

    movements = []
    current_date = start_date

    # Schedule 1-3 random restock dates spread across the history
    num_restocks = random.randint(1, 3)
    restock_days = sorted(random.sample(range(1, days), num_restocks))
    restock_dates = {start_date + timedelta(days=d) for d in restock_days}

    while current_date <= today:
        # Add a restock (IN) movement on scheduled restock dates
        if current_date in restock_dates:
            restock_qty = random.randint(200, 800)
            movements.append(StockMovementDB(
                inventory_id=item.id,
                movement_type="IN",
                quantity=restock_qty,
                movement_date=current_date,
            ))

        # ~70% chance of a sale on any given day
        if random.random() < 0.7:
            quantity = max(1, int(base_demand + random.gauss(0, base_demand * 0.3)))
            movements.append(StockMovementDB(
                inventory_id=item.id,
                movement_type="OUT",
                quantity=quantity,
                movement_date=current_date,
            ))

        current_date += timedelta(days=1)

    db.add_all(movements)


def seed_data(count=100):
    db = SessionLocal()

    print("Deleting existing data...")
    db.query(StockMovementDB).delete()
    db.query(InventoryDB).delete()
    db.commit()

    print(f"Seeding {count} inventory items...")

    items = []
    for _ in range(count):
        drug = random.choice(DRUG_NAMES)
        manufacturer = random.choice(MANUFACTURERS)
        units = random.choice(UNITS)

        price = round(random.uniform(1.50, 40.00), 2)
        quantity = random.randint(50, 500)  # more realistic stock levels

        # Randomise stocked_date across the past year so days_since_restock varies
        stocked_date = datetime.now().date() - timedelta(days=random.randint(180, 365))
        expiry_date = stocked_date + timedelta(days=random.randint(200, 900))

        barcode = str(random.randint(1000000000000, 9999999999999))

        item = InventoryDB(
            drug_name=drug,
            units=units,
            manufacturer=manufacturer,
            price=price,
            stock_quantity=quantity,
            stocked_date=str(stocked_date),
            expiry_date=str(expiry_date),
            barcode=barcode,
        )
        items.append(item)

    db.add_all(items)
    db.commit()

    print("Seeding 365 days of sales history per item...")

    for item in items:
        db.refresh(item)
        generate_movements(db, item, days=365)

    db.commit()
    db.close()

    print("Seeding completed successfully!")


if __name__ == "__main__":
    seed_data()