import random
from datetime import datetime, timedelta

from database import SessionLocal
from models import InventoryDB

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

def random_date(days_range=730):
    """Generate a random date within the next 2 years."""
    today = datetime.now()
    delta = timedelta(days=random.randint(0, days_range))
    return (today + delta).date()

def seed_data(count=100):
    db = SessionLocal()

    print("Deleting existing data...")
    db.query(InventoryDB).delete()
    db.commit()

    print(f"Seeding {count} items...")

    items = []
    for _ in range(count):
        drug = random.choice(DRUG_NAMES)
        manufacturer = random.choice(MANUFACTURERS)
        units = random.choice(UNITS)

        price = round(random.uniform(1.50, 40.00), 2)
        quantity = random.randint(5, 500)

        stocked_date = random_date(days_range=365)
        expiry_date = stocked_date + timedelta(days=random.randint(200, 900))  # 6 months to 2.5 years

        barcode = str(random.randint(1000000000000, 9999999999999))  # 13-digit barcode

        item = InventoryDB(
            drug_name=drug,
            units=units,
            manufacturer=manufacturer,
            price=price,
            stock_quantity=quantity,
            stocked_date=str(stocked_date),
            expiry_date=str(expiry_date),
            barcode=barcode
        )

        items.append(item)

    db.add_all(items)
    db.commit()
    db.close()

    print("Seeding completed successfully!")


if __name__ == "__main__":
    seed_data()
