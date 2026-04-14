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


def generate_movements(db, item: InventoryDB, days: int = 180):
    """
    Generate realistic historical OUT (sales) movements for an item
    going back a given number of days from today.

    Each item gets a base daily demand with some randomness added,
    simulating realistic pharmacy sales patterns.
    Prophet needs at least a few weeks of data to forecast well,
    so we default to 180 days (6 months) of history.
    """
    today = datetime.now().date()
    start_date = today - timedelta(days=days)

    # Each item has a different base demand level — some sell more than others
    base_demand = random.randint(1, 15)

    movements = []
    current_date = start_date

    while current_date <= today:
        # Not every day has a sale — simulate ~70% chance of a sale on any given day
        if random.random() < 0.7:
            # Add some noise around the base demand
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
    # Delete movements first due to foreign key constraint
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
        quantity = random.randint(500, 2000)  # higher quantity to account for sales history

        stocked_date = datetime.now().date() - timedelta(days=200)  # stocked before sales history
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

    print("Seeding 180 days of sales history per item...")

    # Refresh items to get their IDs, then generate movements
    for item in items:
        db.refresh(item)
        generate_movements(db, item, days=180)

    db.commit()
    db.close()

    print("Seeding completed successfully!")
    print(f"  {count} inventory items created")
    print(f"  ~{count * 180 * 7 // 10} sales movements generated (approx)")


if __name__ == "__main__":
    seed_data()