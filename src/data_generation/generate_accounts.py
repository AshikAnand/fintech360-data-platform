import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

RANDOM_SEED = 42

CUSTOMER_FILE = Path(
    "sample_data/raw/customers/customers.csv"
)

OUTPUT_DIRECTORY = Path(
    "sample_data/raw/accounts"
)

OUTPUT_FILE = OUTPUT_DIRECTORY / "accounts.csv"

random.seed(RANDOM_SEED)


# --------------------------------------------------
# Business Reference Data
# --------------------------------------------------

ACCOUNT_TYPES = [
    "WALLET",
    "SAVINGS",
    "CURRENT",
    "PREPAID",
]

ACCOUNT_STATUSES = [
    "ACTIVE",
    "INACTIVE",
    "BLOCKED",
    "CLOSED",
]


# --------------------------------------------------
# Generate One Account
# --------------------------------------------------

def generate_account(
    account_number: int,
    customer_id: str,
    customer_registration_date
) -> dict:
    """
    Generate one valid FinTech360 account
    belonging to an existing customer.
    """

    account_id = f"ACC{account_number:07d}"

    account_type = random.choices(
        ACCOUNT_TYPES,
        weights=[40, 35, 15, 10],
        k=1
    )[0]

    account_status = random.choices(
        ACCOUNT_STATUSES,
        weights=[90, 4, 3, 3],
        k=1
    )[0]

    # Account cannot be opened before
    # the customer joined FinTech360.
    registration_date = pd.to_datetime(
        customer_registration_date
    )

    days_since_registration = (
        pd.Timestamp.today().normalize()
        - registration_date
    ).days

    opened_date = (
        registration_date
        + timedelta(
            days=random.randint(
                0,
                max(days_since_registration, 0)
            )
        )
    )

    # Closed date only applies to closed accounts.
    if account_status == "CLOSED":

        days_since_opening = (
            pd.Timestamp.today().normalize()
            - opened_date
        ).days

        closed_date = (
            opened_date
            + timedelta(
                days=random.randint(
                    0,
                    max(days_since_opening, 0)
                )
            )
        )

    else:
        closed_date = None

    # Generate balance
    current_balance = round(
        random.uniform(
            0,
            500_000
        ),
        2
    )

    # Available balance should normally
    # not exceed current balance.
    available_balance = round(
        random.uniform(
            0,
            current_balance
        ),
        2
    )

    daily_transaction_limit = random.choice(
        [
            25_000,
            50_000,
            100_000,
            200_000,
            500_000,
        ]
    )

    created_at = opened_date

    days_since_creation = (
        pd.Timestamp.today().normalize()
        - created_at
    ).days

    updated_at = (
        created_at
        + timedelta(
            days=random.randint(
                0,
                max(days_since_creation, 0)
            )
        )
    )

    return {
        "account_id": account_id,
        "customer_id": customer_id,
        "account_type": account_type,
        "currency": "INR",
        "current_balance": current_balance,
        "available_balance": available_balance,
        "account_status": account_status,
        "opened_date": opened_date.date(),
        "closed_date": (
            closed_date.date()
            if closed_date is not None
            else None
        ),
        "daily_transaction_limit": daily_transaction_limit,
        "created_at": created_at,
        "updated_at": updated_at,
    }


# --------------------------------------------------
# Generate Accounts
# --------------------------------------------------

def generate_accounts(
    customers_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate accounts for existing FinTech360 customers.

    Each customer receives between 1 and 3 accounts.
    """

    accounts = []

    account_number = 1

    for _, customer in customers_df.iterrows():

        number_of_accounts = random.choices(
            [1, 2, 3],
            weights=[70, 25, 5],
            k=1
        )[0]

        for _ in range(number_of_accounts):

            account = generate_account(
                account_number=account_number,
                customer_id=customer["customer_id"],
                customer_registration_date=customer[
                    "registration_date"
                ]
            )

            accounts.append(account)

            account_number += 1

    return pd.DataFrame(accounts)


# --------------------------------------------------
# Inject Controlled Data Quality Issues
# --------------------------------------------------

def inject_data_quality_issues(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Introduce controlled account source-system
    data-quality problems.
    """

    df = df.copy()

    # 1. Invalid negative balances - 0.5%
    negative_balance_idx = df.sample(
        frac=0.005,
        random_state=201
    ).index

    df.loc[
        negative_balance_idx,
        "current_balance"
    ] = -10_000


    # 2. Invalid currency - 0.2%
    invalid_currency_idx = df.sample(
        frac=0.002,
        random_state=202
    ).index

    df.loc[
        invalid_currency_idx,
        "currency"
    ] = "INVALID"


    # 3. Invalid account status - 0.2%
    invalid_status_idx = df.sample(
        frac=0.002,
        random_state=203
    ).index

    df.loc[
        invalid_status_idx,
        "account_status"
    ] = "UNKNOWN"


    # 4. Duplicate accounts - 1%
    duplicate_rows = df.sample(
        frac=0.01,
        random_state=204
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
# Main Execution
# --------------------------------------------------

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("FINTECH360 - ACCOUNT SOURCE DATA GENERATION")
    print("=" * 60)

    # --------------------------------------------------
    # Step 1: Read Customer Source
    # --------------------------------------------------

    customers_df = pd.read_csv(
        CUSTOMER_FILE
    )

    print(
        f"Customer source rows read: "
        f"{len(customers_df):,}"
    )

    # --------------------------------------------------
    # Step 2: Remove duplicate customers
    # for source relationship generation
    # --------------------------------------------------

    unique_customers_df = (
        customers_df
        .drop_duplicates(
            subset=["customer_id"]
        )
        .copy()
    )

    print(
        f"Unique customers used: "
        f"{len(unique_customers_df):,}"
    )

    # --------------------------------------------------
    # Step 3: Generate Accounts
    # --------------------------------------------------

    accounts_df = generate_accounts(
        unique_customers_df
    )

    base_account_count = len(
        accounts_df
    )

    # --------------------------------------------------
    # Step 4: Inject Source Problems
    # --------------------------------------------------

    accounts_df = inject_data_quality_issues(
        accounts_df
    )

    # --------------------------------------------------
    # Step 5: Save Raw Account Source
    # --------------------------------------------------

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    accounts_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print("-" * 60)

    print(
        f"Base accounts generated: "
        f"{base_account_count:,}"
    )

    print(
        f"Raw account rows: "
        f"{len(accounts_df):,}"
    )

    print(
        f"Unique account IDs: "
        f"{accounts_df['account_id'].nunique():,}"
    )

    print(
        f"Duplicate account IDs: "
        f"{accounts_df['account_id'].duplicated().sum():,}"
    )

    print(
        f"Negative balances: "
        f"{(accounts_df['current_balance'] < 0).sum():,}"
    )

    print(
        f"Invalid currencies: "
        f"{(accounts_df['currency'] == 'INVALID').sum():,}"
    )

    print(
        f"Invalid account statuses: "
        f"{(accounts_df['account_status'] == 'UNKNOWN').sum():,}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print("=" * 60)

    print("\nSample records:\n")

    print(
        accounts_df.head()
    )