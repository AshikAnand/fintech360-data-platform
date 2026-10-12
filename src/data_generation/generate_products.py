from datetime import datetime
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

OUTPUT_DIRECTORY = Path(
    "sample_data/raw/products"
)

OUTPUT_FILE = OUTPUT_DIRECTORY / "products.csv"


# --------------------------------------------------
# Product Master
# --------------------------------------------------

PRODUCTS = [
    {
        "product_id": "PROD001",
        "product_name": "FinTech360 Basic Savings",
        "product_category": "ACCOUNT",
        "product_subcategory": "SAVINGS_ACCOUNT",
        "annual_fee": 0.0,
        "interest_rate": 3.0,
        "min_income_required": 0.0,
        "product_status": "ACTIVE",
        "launch_date": "2022-01-01",
    },
    {
        "product_id": "PROD002",
        "product_name": "FinTech360 Premium Savings",
        "product_category": "ACCOUNT",
        "product_subcategory": "SAVINGS_ACCOUNT",
        "annual_fee": 500.0,
        "interest_rate": 3.5,
        "min_income_required": 500_000.0,
        "product_status": "ACTIVE",
        "launch_date": "2022-06-01",
    },
    {
        "product_id": "PROD003",
        "product_name": "FinTech360 Current Account",
        "product_category": "ACCOUNT",
        "product_subcategory": "CURRENT_ACCOUNT",
        "annual_fee": 1_000.0,
        "interest_rate": 0.0,
        "min_income_required": 0.0,
        "product_status": "ACTIVE",
        "launch_date": "2022-08-01",
    },
    {
        "product_id": "PROD004",
        "product_name": "FinTech360 Digital Wallet",
        "product_category": "WALLET",
        "product_subcategory": "DIGITAL_WALLET",
        "annual_fee": 0.0,
        "interest_rate": None,
        "min_income_required": 0.0,
        "product_status": "ACTIVE",
        "launch_date": "2023-01-01",
    },
    {
        "product_id": "PROD005",
        "product_name": "FinTech360 Debit Card",
        "product_category": "CARD",
        "product_subcategory": "DEBIT_CARD",
        "annual_fee": 250.0,
        "interest_rate": None,
        "min_income_required": 0.0,
        "product_status": "ACTIVE",
        "launch_date": "2023-02-01",
    },
    {
        "product_id": "PROD006",
        "product_name": "FinTech360 Credit Card",
        "product_category": "CARD",
        "product_subcategory": "CREDIT_CARD",
        "annual_fee": 750.0,
        "interest_rate": 36.0,
        "min_income_required": 300_000.0,
        "product_status": "ACTIVE",
        "launch_date": "2023-05-01",
    },
    {
        "product_id": "PROD007",
        "product_name": "FinTech360 Premium Credit Card",
        "product_category": "CARD",
        "product_subcategory": "CREDIT_CARD",
        "annual_fee": 2_500.0,
        "interest_rate": 30.0,
        "min_income_required": 1_000_000.0,
        "product_status": "ACTIVE",
        "launch_date": "2024-01-01",
    },
    {
        "product_id": "PROD008",
        "product_name": "FinTech360 Prepaid Card",
        "product_category": "CARD",
        "product_subcategory": "PREPAID_CARD",
        "annual_fee": 100.0,
        "interest_rate": None,
        "min_income_required": 0.0,
        "product_status": "ACTIVE",
        "launch_date": "2024-03-01",
    },
]


# --------------------------------------------------
# Generate Product Master
# --------------------------------------------------

def generate_products() -> pd.DataFrame:

    products_df = pd.DataFrame(
        PRODUCTS
    )

    current_timestamp = datetime.now()

    products_df["created_at"] = (
        current_timestamp
    )

    products_df["updated_at"] = (
        current_timestamp
    )

    return products_df


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    print()
    print("=" * 60)
    print(
        "FINTECH360 - PRODUCT MASTER GENERATION"
    )
    print("=" * 60)

    products_df = generate_products()

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    products_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"Products generated: "
        f"{len(products_df):,}"
    )

    print(
        f"Unique product IDs: "
        f"{products_df['product_id'].nunique():,}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print("=" * 60)

    print(
        "\nProduct master:\n"
    )

    print(products_df)