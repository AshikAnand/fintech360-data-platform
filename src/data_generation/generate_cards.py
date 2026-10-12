import random
from datetime import timedelta
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

RANDOM_SEED = 42

ACCOUNT_FILE = Path(
    "sample_data/raw/accounts/accounts.csv"
)

OUTPUT_DIRECTORY = Path(
    "sample_data/raw/cards"
)

OUTPUT_FILE = OUTPUT_DIRECTORY / "cards.csv"

random.seed(RANDOM_SEED)


# --------------------------------------------------
# Business Reference Data
# --------------------------------------------------

CARD_TYPES = [
    "PHYSICAL",
    "VIRTUAL",
]

CARD_CATEGORIES = [
    "DEBIT",
    "CREDIT",
]

CARD_NETWORKS = [
    "VISA",
    "MASTERCARD",
    "RUPAY",
]

CARD_STATUSES = [
    "ACTIVE",
    "BLOCKED",
    "EXPIRED",
    "CLOSED",
]


# --------------------------------------------------
# Generate One Card
# --------------------------------------------------

def generate_card(
    card_number: int,
    account_id: str,
    account_opened_date
) -> dict:

    card_id = f"CARD{card_number:07d}"

    card_type = random.choices(
        CARD_TYPES,
        weights=[70, 30],
        k=1
    )[0]

    card_category = random.choices(
        CARD_CATEGORIES,
        weights=[75, 25],
        k=1
    )[0]

    card_network = random.choices(
        CARD_NETWORKS,
        weights=[45, 35, 20],
        k=1
    )[0]

    card_status = random.choices(
        CARD_STATUSES,
        weights=[90, 4, 3, 3],
        k=1
    )[0]

    # ----------------------------------------------
    # Issue Date
    # ----------------------------------------------

    opened_date = pd.to_datetime(
        account_opened_date
    )

    days_since_account_opening = (
        pd.Timestamp.today().normalize()
        - opened_date
    ).days

    issue_date = (
        opened_date
        + timedelta(
            days=random.randint(
                0,
                max(days_since_account_opening, 0)
            )
        )
    )

    # ----------------------------------------------
    # Expiry Date
    # ----------------------------------------------

    expiry_date = (
        issue_date
        + pd.DateOffset(years=5)
    )

    # ----------------------------------------------
    # Card Settings
    # ----------------------------------------------

    international_enabled = random.choices(
        [True, False],
        weights=[40, 60],
        k=1
    )[0]

    contactless_enabled = random.choices(
        [True, False],
        weights=[85, 15],
        k=1
    )[0]

    daily_limit = random.choice(
        [
            25_000,
            50_000,
            100_000,
            200_000,
            500_000,
        ]
    )

    # Safe synthetic last 4 digits only.
    # We deliberately do NOT generate/store
    # full card numbers, CVV or PIN.
    card_last4 = f"{random.randint(0, 9999):04d}"

    created_at = issue_date

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
        "card_id": card_id,
        "account_id": account_id,
        "card_last4": card_last4,
        "card_type": card_type,
        "card_network": card_network,
        "card_category": card_category,
        "issue_date": issue_date.date(),
        "expiry_date": expiry_date.date(),
        "card_status": card_status,
        "international_enabled": international_enabled,
        "contactless_enabled": contactless_enabled,
        "daily_limit": daily_limit,
        "created_at": created_at,
        "updated_at": updated_at,
    }


# --------------------------------------------------
# Generate Cards
# --------------------------------------------------

def generate_cards(
    accounts_df: pd.DataFrame
) -> pd.DataFrame:

    cards = []

    card_number = 1

    for _, account in accounts_df.iterrows():

        account_type = account[
            "account_type"
        ]

        # ------------------------------------------
        # Decide whether this account gets cards
        # ------------------------------------------

        if account_type == "SAVINGS":

            number_of_cards = random.choices(
                [0, 1, 2],
                weights=[10, 80, 10],
                k=1
            )[0]

        elif account_type == "CURRENT":

            number_of_cards = random.choices(
                [0, 1, 2],
                weights=[20, 65, 15],
                k=1
            )[0]

        elif account_type == "WALLET":

            number_of_cards = random.choices(
                [0, 1],
                weights=[70, 30],
                k=1
            )[0]

        elif account_type == "PREPAID":

            number_of_cards = random.choices(
                [0, 1],
                weights=[20, 80],
                k=1
            )[0]

        else:

            number_of_cards = 0

        # ------------------------------------------
        # Generate Cards
        # ------------------------------------------

        for _ in range(number_of_cards):

            card = generate_card(
                card_number=card_number,
                account_id=account[
                    "account_id"
                ],
                account_opened_date=account[
                    "opened_date"
                ]
            )

            cards.append(card)

            card_number += 1

    return pd.DataFrame(cards)


# --------------------------------------------------
# Inject Controlled Data Quality Problems
# --------------------------------------------------

def inject_data_quality_issues(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    # ----------------------------------------------
    # 1. Invalid Daily Limit - 0.5%
    # ----------------------------------------------

    invalid_limit_idx = df.sample(
        frac=0.005,
        random_state=301
    ).index

    df.loc[
        invalid_limit_idx,
        "daily_limit"
    ] = -10_000


    # ----------------------------------------------
    # 2. Invalid Card Status - 0.2%
    # ----------------------------------------------

    invalid_status_idx = df.sample(
        frac=0.002,
        random_state=302
    ).index

    df.loc[
        invalid_status_idx,
        "card_status"
    ] = "UNKNOWN"


    # ----------------------------------------------
    # 3. Invalid Card Network - 0.2%
    # ----------------------------------------------

    invalid_network_idx = df.sample(
        frac=0.002,
        random_state=303
    ).index

    df.loc[
        invalid_network_idx,
        "card_network"
    ] = "INVALID"


    # ----------------------------------------------
    # 4. Orphan Account IDs - 0.2%
    # ----------------------------------------------

    orphan_account_idx = df.sample(
        frac=0.002,
        random_state=304
    ).index

    for counter, idx in enumerate(
        orphan_account_idx,
        start=1
    ):

        df.loc[
            idx,
            "account_id"
        ] = f"ACC_INVALID_{counter:04d}"


    # ----------------------------------------------
    # 5. Duplicate Cards - 1%
    # ----------------------------------------------

    duplicate_rows = df.sample(
        frac=0.01,
        random_state=305
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
    print(
        "FINTECH360 - CARD SOURCE DATA GENERATION"
    )
    print("=" * 60)

    # ----------------------------------------------
    # Step 1: Read Accounts
    # ----------------------------------------------

    accounts_df = pd.read_csv(
        ACCOUNT_FILE
    )

    print(
        f"Account source rows read: "
        f"{len(accounts_df):,}"
    )

    # ----------------------------------------------
    # Step 2: Use unique accounts
    # ----------------------------------------------

    unique_accounts_df = (
        accounts_df
        .drop_duplicates(
            subset=["account_id"]
        )
        .copy()
    )

    print(
        f"Unique accounts used: "
        f"{len(unique_accounts_df):,}"
    )

    # ----------------------------------------------
    # Step 3: Generate Cards
    # ----------------------------------------------

    cards_df = generate_cards(
        unique_accounts_df
    )

    base_card_count = len(
        cards_df
    )

    # ----------------------------------------------
    # Step 4: Inject Source Problems
    # ----------------------------------------------

    cards_df = inject_data_quality_issues(
        cards_df
    )

    # ----------------------------------------------
    # Step 5: Save Raw Cards
    # ----------------------------------------------

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    cards_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ----------------------------------------------
    # Summary
    # ----------------------------------------------

    print("-" * 60)

    print(
        f"Base cards generated: "
        f"{base_card_count:,}"
    )

    print(
        f"Raw card rows: "
        f"{len(cards_df):,}"
    )

    print(
        f"Unique card IDs: "
        f"{cards_df['card_id'].nunique():,}"
    )

    print(
        f"Duplicate card IDs: "
        f"{cards_df['card_id'].duplicated().sum():,}"
    )

    print(
        f"Invalid daily limits: "
        f"{(cards_df['daily_limit'] < 0).sum():,}"
    )

    print(
        f"Invalid card statuses: "
        f"{(cards_df['card_status'] == 'UNKNOWN').sum():,}"
    )

    print(
        f"Invalid card networks: "
        f"{(cards_df['card_network'] == 'INVALID').sum():,}"
    )

    print(
        f"Orphan account IDs: "
        f"{cards_df['account_id'].astype(str).str.startswith('ACC_INVALID_').sum():,}"
    )

    print(
        f"Saved to: "
        f"{OUTPUT_FILE}"
    )

    print("=" * 60)

    print("\nSample records:\n")

    print(
        cards_df.head()
    )