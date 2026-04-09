import random
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import InventoryDB, StockMovementDB

# ------------------------------------------------------------------ #
#  Static data pools
# ------------------------------------------------------------------ #
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

# ------------------------------------------------------------------ #
#  Demand profiles — controls how "busy" a drug is
#  Each profile defines:
#    sale_days_per_month : average days per month with at least one sale
#    qty_range           : (min, max) units sold on a sale day
#    trend               : "flat" | "growing" | "declining"
#    seasonal_boost      : list of months (1-12) where demand spikes ~2x
# ------------------------------------------------------------------ #
DEMAND_PROFILES = [
    # High-volume, flat demand  (e.g. Paracetamol, Ibuprofen)
    {"sale_days_per_month": 25, "qty_range": (10, 60), "trend": "flat",     "seasonal_boost": []},
    # Medium-volume, growing    (e.g. Vitamin D — awareness growing)
    {"sale_days_per_month": 15, "qty_range": (5,  30), "trend": "growing",  "seasonal_boost": [11, 12, 1, 2]},
    # Low-volume, seasonal      (e.g. Cetirizine / hay fever)
    {"sale_days_per_month": 8,  "qty_range": (2,  15), "trend": "flat",     "seasonal_boost": [3, 4, 5, 6]},
    # Sporadic, declining       (e.g. older antibiotic being replaced)
    {"sale_days_per_month": 5,  "qty_range": (1,  10), "trend": "declining","seasonal_boost": []},
    # Very high volume          (e.g. Aspirin / daily use)
    {"sale_days_per_month": 28, "qty_range": (20, 80), "trend": "flat",     "seasonal_boost": []},
]


def random_future_date(days_range: int = 730) -> str:
    today = datetime.now()
    return (today + timedelta(days=random.randint(0, days_range))).date()


def generate_sales_history(
    inventory_id: int,
    initial_stock: int,
    stocked_date,
    profile: dict,
    history_days: int = 365
) -> list[StockMovementDB]:
    """
    Generates a realistic stream of OUT movements over the past `history_days` days.
    Respects the demand profile (volume, trend, seasonality).
    Never sells more than remaining stock.
    """
    movements = []
    today = datetime.now().date()
    start_date = today - timedelta(days=history_days)

    # Don't generate sales before the item was stocked
    if stocked_date > start_date:
        start_date = stocked_date

    remaining_stock = initial_stock
    total_days = (today - start_date).days

    if total_days <= 0:
        return []

    sale_prob_per_day = profile["sale_days_per_month"] / 30.0
    qty_min, qty_max = profile["qty_range"]
    trend = profile["trend"]
    seasonal_months = profile["seasonal_boost"]

    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)

        if remaining_stock <= 0:
            break

        # Apply trend multiplier — grows/declines over the year
        progress = day_offset / max(total_days, 1)   # 0.0 → 1.0
        if trend == "growing":
            trend_multiplier = 0.6 + (0.8 * progress)   # starts slow, ramps up
        elif trend == "declining":
            trend_multiplier = 1.4 - (0.8 * progress)   # starts high, fades
        else:
            trend_multiplier = 1.0

        # Apply seasonal multiplier
        seasonal_multiplier = 1.8 if current_date.month in seasonal_months else 1.0

        # Final probability of a sale happening today
        effective_prob = min(sale_prob_per_day * trend_multiplier * seasonal_multiplier, 1.0)

        if random.random() > effective_prob:
            continue  # no sale today

        # Decide quantity sold today
        base_qty = random.randint(qty_min, qty_max)
        qty = max(1, int(base_qty * trend_multiplier * seasonal_multiplier))
        qty = min(qty, remaining_stock)  # can't sell what you don't have

        movements.append(StockMovementDB(
            inventory_id=inventory_id,
            movement_type="OUT",
            quantity=qty,
            movement_date=current_date,
        ))

        remaining_stock -= qty

    return movements


def seed_data(count: int = 50, history_days: int = 365):
    db = SessionLocal()

    print("Deleting existing stock movements...")
    db.query(StockMovementDB).delete()
    print("Deleting existing inventory...")
    db.query(InventoryDB).delete()
    db.commit()

    print(f"Seeding {count} inventory items with {history_days} days of sales history...\n")

    today = datetime.now().date()

    for i in range(count):
        drug      = random.choice(DRUG_NAMES)
        mfr       = random.choice(MANUFACTURERS)
        units     = random.choice(UNITS)
        price     = round(random.uniform(1.50, 40.00), 2)

        # Stock high enough that sales history won't zero it out immediately
        initial_stock = random.randint(200, 1000)

        stocked_date  = today - timedelta(days=random.randint(history_days, history_days + 180))
        expiry_date   = stocked_date + timedelta(days=random.randint(365, 1095))
        barcode       = str(random.randint(1_000_000_000_000, 9_999_999_999_999))

        item = InventoryDB(
            drug_name      = drug,
            manufacturer   = mfr,
            units          = units,
            price          = price,
            stock_quantity = initial_stock,
            stocked_date   = stocked_date,
            expiry_date    = expiry_date,
            barcode        = barcode,
        )
        db.add(item)
        db.flush()  # get item.id before commit

        # Log the initial IN movement
        db.add(StockMovementDB(
            inventory_id   = item.id,
            movement_type  = "IN",
            quantity       = initial_stock,
            movement_date  = stocked_date,
        ))

        # Pick a demand profile (cycle through them so we get variety)
        profile = DEMAND_PROFILES[i % len(DEMAND_PROFILES)]

        # Generate realistic OUT movements
        sales = generate_sales_history(
            inventory_id  = item.id,
            initial_stock = initial_stock,
            stocked_date  = stocked_date,
            profile       = profile,
            history_days  = history_days,
        )

        total_sold = sum(s.quantity for s in sales)

        # Update current stock to reflect actual sales
        item.stock_quantity = max(0, initial_stock - total_sold)

        db.add_all(sales)

        print(f"  [{i+1:>3}/{count}] {drug:<22} | profile: {profile['trend']:<10} "
              f"| {len(sales):>4} sale days | {total_sold:>5} units sold "
              f"| stock remaining: {item.stock_quantity}")

    db.commit()
    db.close()
    print("\nSeeding complete!")


if __name__ == "__main__":
    seed_data(count=50, history_days=365)