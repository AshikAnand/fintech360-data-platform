import random
from datetime import timedelta
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

RANDOM_SEED = 42

CUSTOMER_FILE = Path(
    "sample_data/raw/customers/customers.csv"
)

PRODUCT_FILE = Path(
    "sample_data/raw/products/products.csv"
)

OUTPUT_DIRECTORY = Path(
    "sample_data/raw/customer_products"
)

OUTPUT_FILE = (
    OUTPUT_DIRECTORY
    / "customer_products.csv"
)

random.seed(RANDOM_SEED)


# --------------------------------------------------
# Generate Customer Product Relationships
# --------------------------------------------------

def generate_customer_products(
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame
) -> pd.DataFrame:

    relationships = []

    relationship_number = 1

    product_records = (
        products_df.to_dict("records")
    )

    for _, customer in customers_df.iterrows():

        registration_date = pd.to_datetime(
            customer["registration_date"]
        )

        # Most customers use 1-3 products.
        number_of_products = random.choices(
            [1, 2, 3, 4],
            weights=[35, 40, 20, 5],
            k=1
        )[0]

        selected_products = random.sample(
            product_records,
            k=min(
                number_of_products,
                len(product_records)
            )
        )

        for product in selected_products:

            launch_date = pd.to_datetime(
                product["launch_date"]
            )

            # Customer cannot enroll before:
            # 1. customer registration
            # 2. product launch
            earliest_enrollment_date = max(
                registration_date,
                launch_date
            )

            today = (
                pd.Timestamp.today()
                .normalize()
            )

            days_available = (
                today
                - earliest_enrollment_date
            ).days

            if days_available <= 0:

                enrollment_date = today

            else:

                enrollment_date = (
                    earliest_enrollment_date
                    + timedelta(
                        days=random.randint(
                            0,
                            days_available
                        )
                    )
                )

            status = random.choices(
                [
                    "ACTIVE",
                    "INACTIVE",
                    "CLOSED",
                ],
                weights=[90, 5, 5],
                k=1
            )[0]

            activation_date = (
                enrollment_date
                + timedelta(
                    days=random.randint(
                        0,
                        3
                    )
                )
            )

            if status == "CLOSED":

                days_since_activation = (
                    today
                    - activation_date
                ).days

                if days_since_activation <= 0:

                    closure_date = (
                        activation_date
                    )

                else:

                    closure_date = (
                        activation_date
                        + timedelta(
                            days=random.randint(
                                0,
                                days_since_activation
                            )
                        )
                    )

            else:

                closure_date = None

            customer_product_id = (
                f"CP{relationship_number:08d}"
            )

            relationships.append(
                {
                    "customer_product_id":
                        customer_product_id,

                    "customer_id":
                        customer["customer_id"],

                    "product_id":
                        product["product_id"],

                    "enrollment_date":
                        enrollment_date.date(),

                    "status":
                        status,

                    "activation_date":
                        activation_date.date(),

                    "closure_date":
                        (
                            closure_date.date()
                            if closure_date
                            is not None
                            else None
                        ),

                    "created_at":
                        enrollment_date,

                    "updated_at":
                        (
                            closure_date
                            if closure_date
                            is not None
                            else activation_date
                        ),
                }
            )

            relationship_number += 1

    return pd.DataFrame(
        relationships
    )


# --------------------------------------------------
# Inject Controlled Data Quality Problems
# --------------------------------------------------

def inject_data_quality_issues(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    # --------------------------------------------------
    # 1. Invalid status - 0.2%
    # --------------------------------------------------

    invalid_status_idx = df.sample(
        frac=0.002,
        random_state=701
    ).index

    df.loc[
        invalid_status_idx,
        "status"
    ] = "UNKNOWN"


    # --------------------------------------------------
    # 2. Orphan Product ID - 0.2%
    # --------------------------------------------------

    orphan_product_idx = df.sample(
        frac=0.002,
        random_state=702
    ).index

    for counter, idx in enumerate(
        orphan_product_idx,
        start=1
    ):

        df.loc[
            idx,
            "product_id"
        ] = (
            f"PROD_INVALID_{counter:04d}"
        )


    # --------------------------------------------------
    # 3. Missing Customer ID - 0.1%
    # --------------------------------------------------

    missing_customer_idx = df.sample(
        frac=0.001,
        random_state=703
    ).index

    df.loc[
        missing_customer_idx,
        "customer_id"
    ] = None


    # --------------------------------------------------
    # 4. Duplicate relationships - 1%
    # --------------------------------------------------

    duplicate_rows = df.sample(
        frac=0.01,
        random_state=704
    )

    df = pd.concat(
        [
            df,
            duplicate_rows
        ],
        ignore_index=True
    )

    return df


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    print()

    print("=" * 65)

    print(
        "FINTECH360 - CUSTOMER PRODUCT GENERATION"
    )

    print("=" * 65)

    # --------------------------------------------------
    # Load Customers
    # --------------------------------------------------

    customers_df = pd.read_csv(
        CUSTOMER_FILE
    )

    customers_df = (
        customers_df
        .drop_duplicates(
            subset=["customer_id"]
        )
        .copy()
    )

    # --------------------------------------------------
    # Load Product Master
    # --------------------------------------------------

    products_df = pd.read_csv(
        PRODUCT_FILE
    )

    # --------------------------------------------------
    # Generate relationships
    # --------------------------------------------------

    customer_products_df = (
        generate_customer_products(
            customers_df,
            products_df
        )
    )

    base_relationship_count = len(
        customer_products_df
    )

    # --------------------------------------------------
    # Inject source problems
    # --------------------------------------------------

    customer_products_df = (
        inject_data_quality_issues(
            customer_products_df
        )
    )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    customer_products_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print(
        f"Base relationships generated: "
        f"{base_relationship_count:,}"
    )

    print(
        f"Raw relationship rows: "
        f"{len(customer_products_df):,}"
    )

    print(
        f"Unique relationship IDs: "
        f"{customer_products_df['customer_product_id'].nunique():,}"
    )

    print(
        f"Duplicate relationship IDs: "
        f"{customer_products_df['customer_product_id'].duplicated().sum():,}"
    )

    print(
        f"Missing customer IDs: "
        f"{customer_products_df['customer_id'].isna().sum():,}"
    )

    print(
        f"Orphan product IDs: "
        f"{customer_products_df['product_id'].astype(str).str.startswith('PROD_INVALID_').sum():,}"
    )

    print(
        f"Invalid statuses: "
        f"{(customer_products_df['status'] == 'UNKNOWN').sum():,}"
    )

    print(
        f"Saved to: "
        f"{OUTPUT_FILE}"
    )

    print("=" * 65)

    print(
        "\nSample records:\n"
    )

    print(
        customer_products_df.head()
    )