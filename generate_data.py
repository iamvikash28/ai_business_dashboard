"""
generate_data.py
Generates a synthetic sales dataset for the AI Business Insights Dashboard.

Why synthetic data with built-in patterns?
So the AI Q&A demo answers something real: e.g. "Why did sales drop last
month?" should have an actual answer baked into the data (a real dip),
and "which products are losing revenue?" should point to real decliners.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

# ---- Config ----
N_ORDERS = 6000
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 12, 31)

REGIONS = ["North", "South", "East", "West", "Central"]

PRODUCTS = {
    # name: (category, base_price, trend) trend: 'growing' | 'stable' | 'declining'
    "Aero Laptop 14": ("Electronics", 950, "growing"),
    "Aero Laptop 16": ("Electronics", 1300, "stable"),
    "Buzz Wireless Earbuds": ("Electronics", 80, "growing"),
    "Buzz Bluetooth Speaker": ("Electronics", 60, "declining"),
    "Comfy Office Chair": ("Furniture", 220, "stable"),
    "Comfy Standing Desk": ("Furniture", 410, "growing"),
    "Comfy Bookshelf": ("Furniture", 150, "declining"),
    "Sharp Notebook Set": ("Office Supplies", 12, "stable"),
    "Sharp Pen Pack": ("Office Supplies", 8, "declining"),
    "Sharp Whiteboard": ("Office Supplies", 65, "stable"),
    "Vivid Monitor 27in": ("Electronics", 280, "growing"),
    "Vivid Webcam HD": ("Electronics", 45, "declining"),
}

PRODUCT_NAMES = list(PRODUCTS.keys())

# A deliberate revenue dip in November 2025 (most recent month before "today")
DIP_MONTH = (2025, 11)
DIP_FACTOR = 0.55  # 45% drop that month, to be "explained" by the AI


def month_seasonality(d: datetime) -> float:
    """Mild seasonality: higher in Nov/Dec (holiday), lower in Feb."""
    seasonal = {
        1: 0.95, 2: 0.85, 3: 0.95, 4: 1.0, 5: 1.0, 6: 1.0,
        7: 0.95, 8: 0.95, 9: 1.0, 10: 1.05, 11: 1.25, 12: 1.3,
    }
    return seasonal[d.month]


def trend_factor(trend: str, d: datetime) -> float:
    """Linear-ish trend across the 2-year window."""
    days_elapsed = (d - START_DATE).days
    total_days = (END_DATE - START_DATE).days
    progress = days_elapsed / total_days  # 0 -> 1

    if trend == "growing":
        return 0.7 + 0.8 * progress  # grows from 0.7x to 1.5x
    elif trend == "declining":
        return 1.3 - 0.9 * progress  # shrinks from 1.3x to 0.4x
    else:
        return 1.0


def random_date() -> datetime:
    total_days = (END_DATE - START_DATE).days
    offset = np.random.randint(0, total_days)
    return START_DATE + timedelta(days=int(offset))


def build_dataset(n=N_ORDERS) -> pd.DataFrame:
    rows = []
    order_id = 100000

    # Sample dates with weighting so we have ~equal density per day,
    # then re-weight by product trend/seasonality via acceptance sampling.
    for _ in range(n):
        d = random_date()
        product = np.random.choice(PRODUCT_NAMES)
        category, base_price, trend = PRODUCTS[product]

        weight = trend_factor(trend, d) * month_seasonality(d)
        if (d.year, d.month) == DIP_MONTH:
            weight *= DIP_FACTOR

        # Acceptance sampling: skip some rows based on weight to create
        # realistic volume differences without changing row count logic much.
        if np.random.random() > min(weight / 1.6, 1.0):
            continue

        qty = max(1, int(np.random.poisson(2)))
        price = base_price * np.random.uniform(0.92, 1.08)
        discount = np.random.choice([0, 0, 0, 0.05, 0.1, 0.15], p=[0.55, 0.1, 0.1, 0.1, 0.1, 0.05])
        revenue = round(qty * price * (1 - discount), 2)
        cost = round(qty * price * np.random.uniform(0.55, 0.75), 2)
        profit = round(revenue - cost, 2)

        order_id += 1
        rows.append({
            "order_id": order_id,
            "order_date": d.strftime("%Y-%m-%d"),
            "product": product,
            "category": category,
            "region": np.random.choice(REGIONS),
            "quantity": qty,
            "unit_price": round(price, 2),
            "discount": discount,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
        })

    df = pd.DataFrame(rows)

    # Inject a few messy/missing values on purpose, since "data cleaning"
    # is a stated feature of the project and the cleaning step needs
    # something real to do.
    messy_idx = np.random.choice(df.index, size=int(len(df) * 0.01), replace=False)
    df.loc[messy_idx, "region"] = None

    dup_rows = df.sample(15, random_state=1)
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df.sort_values("order_date").reset_index(drop=True)


if __name__ == "__main__":
    df = build_dataset()
    out_path = "data/raw_sales.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} rows -> {out_path}")
    print(df.head())
