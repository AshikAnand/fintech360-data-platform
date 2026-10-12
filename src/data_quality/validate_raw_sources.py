from pathlib import Path
import pandas as pd


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "sample_data" / "raw"


# --------------------------------------------------
# DATASET CONFIGURATION
# --------------------------------------------------

DATASETS = {
    "customers": {
        "file": RAW_ROOT / "customers" / "customers.csv",
        "pk": "customer_id",
    },
    "accounts": {
        "file": RAW_ROOT / "accounts" / "accounts.csv",
        "pk": "account_id",
    },
    "cards": {
        "file": RAW_ROOT / "cards" / "cards.csv",
        "pk": "card_id",
    },
    "merchants": {
        "file": RAW_ROOT / "merchants" / "merchants.csv",
        "pk": "merchant_id",
    },
    "payments": {
        "file": RAW_ROOT / "payments" / "payments.csv",
        "pk": "payment_id",
    },
    "transactions": {
        "file": RAW_ROOT / "transactions" / "transactions.csv",
        "pk": "transaction_id",
    },
    "products": {
        "file": RAW_ROOT / "products" / "products.csv",
        "pk": "product_id",
    },
    "customer_products": {
        "file": RAW_ROOT / "customer_products" / "customer_products.csv",
        "pk": "customer_product_id",
    },
}


# --------------------------------------------------
# FOREIGN KEY RELATIONSHIPS
# --------------------------------------------------

FOREIGN_KEYS = [
    ("accounts", "customer_id", "customers", "customer_id"),
    ("cards", "account_id", "accounts", "account_id"),

    ("payments", "customer_id", "customers", "customer_id"),
    ("payments", "account_id", "accounts", "account_id"),
    ("payments", "merchant_id", "merchants", "merchant_id"),
    ("payments", "card_id", "cards", "card_id"),

    ("transactions", "account_id", "accounts", "account_id"),
    ("transactions", "payment_id", "payments", "payment_id"),

    (
        "customer_products",
        "customer_id",
        "customers",
        "customer_id",
    ),
    (
        "customer_products",
        "product_id",
        "products",
        "product_id",
    ),
]


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

def load_datasets():

    data = {}

    print("\n" + "=" * 70)
    print("FINTECH360 RAW SOURCE VALIDATION")
    print("=" * 70)

    for name, config in DATASETS.items():

        path = config["file"]

        if not path.exists():
            print(f"[ERROR] {name}: file not found -> {path}")
            continue

        df = pd.read_csv(path)

        data[name] = df

        print(
            f"[OK] {name:<20} "
            f"rows={len(df):>8,} "
            f"columns={len(df.columns):>3}"
        )

    return data


# --------------------------------------------------
# PRIMARY KEY CHECKS
# --------------------------------------------------

def validate_primary_keys(data):

    print("\n" + "=" * 70)
    print("PRIMARY KEY VALIDATION")
    print("=" * 70)

    for name, df in data.items():

        pk = DATASETS[name]["pk"]

        null_count = df[pk].isna().sum()
        duplicate_count = df[pk].duplicated().sum()

        print(
            f"{name:<20} "
            f"PK={pk:<22} "
            f"nulls={null_count:<6} "
            f"duplicates={duplicate_count}"
        )


# --------------------------------------------------
# FOREIGN KEY CHECKS
# --------------------------------------------------

def validate_foreign_keys(data):

    print("\n" + "=" * 70)
    print("FOREIGN KEY VALIDATION")
    print("=" * 70)

    for (
        child_table,
        child_column,
        parent_table,
        parent_column,
    ) in FOREIGN_KEYS:

        if child_table not in data or parent_table not in data:
            continue

        child_df = data[child_table]
        parent_df = data[parent_table]

        child_values = child_df[child_column]
        parent_values = set(
            parent_df[parent_column].dropna().unique()
        )

        # Nullable FK values are not automatically orphans.
        non_null_values = child_values.dropna()

        orphan_mask = ~non_null_values.isin(parent_values)
        orphan_count = orphan_mask.sum()

        print(
            f"{child_table}.{child_column:<18} "
            f"→ {parent_table}.{parent_column:<20} "
            f"orphans={orphan_count}"
        )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    data = load_datasets()

    validate_primary_keys(data)

    validate_foreign_keys(data)

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()