"""
clean_data.py
Cleans the raw synthetic sales data and writes a cleaned CSV that the
SQL loader will use. Run after generate_data.py.
"""

import pandas as pd


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- Fix types ---
    df["order_date"] = pd.to_datetime(df["order_date"])

    # --- Remove duplicates (exact duplicate orders) ---
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"])
    removed = before - len(df)
    if removed:
        print(f"Removed {removed} duplicate rows")

    # --- Handle missing values ---
    missing_region = df["region"].isna().sum()
    df["region"] = df["region"].fillna("Unknown")
    if missing_region:
        print(f"Filled {missing_region} missing region values with 'Unknown'")

    # --- Derived columns used throughout the dashboard ---
    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.month
    df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
    df["profit_margin"] = (df["profit"] / df["revenue"]).round(4)

    # --- Sanity checks: drop impossible rows ---
    bad = df[(df["revenue"] <= 0) | (df["quantity"] <= 0)]
    if len(bad):
        print(f"Dropping {len(bad)} rows with non-positive revenue/quantity")
    df = df[(df["revenue"] > 0) & (df["quantity"] > 0)]

    return df.reset_index(drop=True)


if __name__ == "__main__":
    raw = pd.read_csv("data/raw_sales.csv")
    cleaned = clean(raw)
    cleaned.to_csv("data/clean_sales.csv", index=False)
    print(f"Cleaned dataset: {len(cleaned)} rows -> data/clean_sales.csv")
    print(cleaned.dtypes)
