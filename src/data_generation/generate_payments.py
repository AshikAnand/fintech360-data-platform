import random
from datetime import timedelta
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

NUM_PAYMENTS = 100_000
RANDOM_SEED = 42

CUSTOMER_FILE = Path(
    "sample_data/raw/customers/customers.csv"
)

ACCOUNT_FILE = Path(
    "sample_data/raw/accounts/accounts.csv"
)

CARD_FILE = Path(
    "sample_data/raw/cards/cards.csv"
)

MERCHANT_FILE = Path(
    "sample_data/raw/merchants/merchants.csv"
)

OUTPUT_DIRECTORY = Path(
    "sample_data/raw/payments"
)

OUTPUT_FILE = OUTPUT_DIRECTORY / "payments.csv"

random.seed(RANDOM_SEED)


# --------------------------------------------------
# Business Reference Data
# --------------------------------------------------

PAYMENT_METHODS = [
    "UPI",
    "CARD",
    "WALLET",
    "BANK_TRANSFER",
]

PAYMENT_STATUSES = [
    "SUCCESS",
    "FAILED",
]

FAILURE_REASONS = [
    "INSUFFICIENT_FUNDS",
    "TIMEOUT",
    "BANK_DECLINED",
    "INVALID_DETAILS",
    "LIMIT_EXCEEDED",
    "NETWORK_ERROR",
    "SUSPECTED_FRAUD",
]

GATEWAYS = [
    "GATEWAY_A",
    "GATEWAY_B",
    "GATEWAY_C",
]

DEVICE_TYPES = [
    "ANDROID",
    "IOS",
    "WEB",
]

CHANNELS = [
    "MOBILE_APP",
    "WEB",
    "POS",
]


# --------------------------------------------------
# Prepare Source Data
# --------------------------------------------------

def prepare_source_data(
    customers_df,
    accounts_df,
    cards_df,
    merchants_df,
):

    # --------------------------------------------------
    # Remove deliberately injected duplicate source rows
    #
    # This is NOT Silver cleansing.
    # We only need one parent record per business key
    # while generating logically connected child records.
    # --------------------------------------------------

    customers_df = (
        customers_df
        .drop_duplicates(
            subset=["customer_id"]
        )
        .copy()
    )

    accounts_df = (
        accounts_df
        .drop_duplicates(
            subset=["account_id"]
        )
        .copy()
    )

    cards_df = (
        cards_df
        .drop_duplicates(
            subset=["card_id"]
        )
        .copy()
    )

    merchants_df = (
        merchants_df
        .drop_duplicates(
            subset=["merchant_id"]
        )
        .copy()
    )

    # --------------------------------------------------
    # Remove deliberately corrupted source records
    # from the synthetic relationship generator.
    #
    # Important:
    # We are NOT performing Silver cleansing here.
    #
    # We only need valid parent entities to generate
    # logically connected child payment records.
    # --------------------------------------------------

    accounts_df = accounts_df[
        accounts_df["account_status"].isin(
            [
                "ACTIVE",
                "INACTIVE",
                "BLOCKED",
                "CLOSED",
            ]
        )
    ].copy()

    cards_df = cards_df[
        cards_df["card_status"].isin(
            [
                "ACTIVE",
                "BLOCKED",
                "EXPIRED",
                "CLOSED",
            ]
        )
    ].copy()

    cards_df = cards_df[
        ~cards_df["account_id"]
        .astype(str)
        .str.startswith("ACC_INVALID_")
    ].copy()

    merchants_df = merchants_df[
        merchants_df["merchant_status"].isin(
            [
                "ACTIVE",
                "INACTIVE",
                "SUSPENDED",
            ]
        )
    ].copy()

    return (
        customers_df,
        accounts_df,
        cards_df,
        merchants_df,
    )


# --------------------------------------------------
# Build Lookup Structures
# --------------------------------------------------

def build_lookups(
    accounts_df,
    cards_df,
):

    # Customer -> Accounts
    customer_accounts = (
        accounts_df
        .groupby("customer_id")["account_id"]
        .apply(list)
        .to_dict()
    )

    # Account -> Cards
    account_cards = (
        cards_df
        .groupby("account_id")["card_id"]
        .apply(list)
        .to_dict()
    )

    return (
        customer_accounts,
        account_cards,
    )


# --------------------------------------------------
# Generate Payment Timestamp
# --------------------------------------------------

def generate_payment_timestamp(
    account_opened_date,
    merchant_onboarding_date,
):

    account_opened_date = pd.to_datetime(
        account_opened_date
    )

    merchant_onboarding_date = pd.to_datetime(
        merchant_onboarding_date
    )

    # Payment cannot happen before either
    # the account or merchant exists.
    earliest_date = max(
        account_opened_date,
        merchant_onboarding_date,
    )

    today = pd.Timestamp.today().normalize()

    days_available = (
        today - earliest_date
    ).days

    if days_available <= 0:
        payment_date = today

    else:
        payment_date = (
            earliest_date
            + timedelta(
                days=random.randint(
                    0,
                    days_available,
                )
            )
        )

    # Add realistic time of day
    payment_timestamp = (
        payment_date
        + timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
    )

    return payment_timestamp


# --------------------------------------------------
# Generate One Payment
# --------------------------------------------------

def generate_payment(
    payment_number,
    customer_id,
    account,
    merchant,
    account_cards,
):

    payment_id = (
        f"PAY{payment_number:09d}"
    )

    payment_method = random.choices(
        PAYMENT_METHODS,
        weights=[45, 35, 15, 5],
        k=1,
    )[0]

    # --------------------------------------------------
    # Card logic
    # --------------------------------------------------

    card_id = None

    available_cards = account_cards.get(
        account["account_id"],
        [],
    )

    # If CARD was selected but the account has
    # no card, fall back to another method.
    if payment_method == "CARD":

        if available_cards:

            card_id = random.choice(
                available_cards
            )

        else:

            payment_method = random.choice(
                [
                    "UPI",
                    "WALLET",
                    "BANK_TRANSFER",
                ]
            )

    # --------------------------------------------------
    # Amount
    # --------------------------------------------------

    amount = round(
        random.uniform(
            50,
            50_000,
        ),
        2,
    )

    # --------------------------------------------------
    # Payment Status
    # --------------------------------------------------

    payment_status = random.choices(
        PAYMENT_STATUSES,
        weights=[92, 8],
        k=1,
    )[0]

    if payment_status == "FAILED":

        failure_reason = random.choice(
            FAILURE_REASONS
        )

    else:

        failure_reason = None

    # --------------------------------------------------
    # Timestamp
    # --------------------------------------------------

    payment_timestamp = (
        generate_payment_timestamp(
            account["opened_date"],
            merchant["onboarding_date"],
        )
    )

    return {
        "payment_id": payment_id,
        "customer_id": customer_id,
        "account_id": account["account_id"],
        "merchant_id": merchant["merchant_id"],
        "card_id": card_id,
        "payment_method": payment_method,
        "amount": amount,
        "currency": "INR",
        "payment_status": payment_status,
        "failure_reason": failure_reason,
        "gateway": random.choice(
            GATEWAYS
        ),
        "payment_timestamp": payment_timestamp,
        "device_type": random.choice(
            DEVICE_TYPES
        ),
        "channel": random.choice(
            CHANNELS
        ),
        "created_at": payment_timestamp,
    }


# --------------------------------------------------
# Generate Payments
# --------------------------------------------------

def generate_payments(
    num_payments,
    customers_df,
    accounts_df,
    merchants_df,
    customer_accounts,
    account_cards,
):

    payments = []

    # --------------------------------------------------
    # Account lookup
    #
    # account_id becomes the dictionary key after
    # set_index(), so it is no longer contained inside
    # each account dictionary.
    # --------------------------------------------------

    account_lookup = (
        accounts_df
        .set_index("account_id")
        .to_dict("index")
    )

    eligible_customers = [
        customer_id
        for customer_id
        in customers_df["customer_id"]
        if customer_id
        in customer_accounts
    ]

    merchant_records = (
        merchants_df
        .to_dict("records")
    )

    for payment_number in range(
        1,
        num_payments + 1,
    ):

        customer_id = random.choice(
            eligible_customers
        )

        account_id = random.choice(
            customer_accounts[
                customer_id
            ]
        )

        # --------------------------------------------------
        # IMPORTANT FIX
        #
        # account_id was used as the index when creating
        # account_lookup. Therefore it is not automatically
        # present inside the returned account dictionary.
        #
        # Create a copy and restore account_id explicitly.
        # --------------------------------------------------

        account = account_lookup[
            account_id
        ].copy()

        account["account_id"] = account_id

        merchant = random.choice(
            merchant_records
        )

        payment = generate_payment(
            payment_number=payment_number,
            customer_id=customer_id,
            account=account,
            merchant=merchant,
            account_cards=account_cards,
        )

        payments.append(
            payment
        )

    return pd.DataFrame(
        payments
    )


# --------------------------------------------------
# Inject Controlled Data Quality Problems
# --------------------------------------------------

def inject_data_quality_issues(
    df,
):

    df = df.copy()

    # --------------------------------------------------
    # 1. Negative payment amount - 0.2%
    # --------------------------------------------------

    negative_amount_idx = df.sample(
        frac=0.002,
        random_state=501,
    ).index

    df.loc[
        negative_amount_idx,
        "amount",
    ] = -500

    # --------------------------------------------------
    # 2. Invalid payment status - 0.1%
    # --------------------------------------------------

    invalid_status_idx = df.sample(
        frac=0.001,
        random_state=502,
    ).index

    df.loc[
        invalid_status_idx,
        "payment_status",
    ] = "UNKNOWN"

    # --------------------------------------------------
    # 3. CARD payment without card_id - 0.2%
    # --------------------------------------------------

    card_payments = df[
        df["payment_method"] == "CARD"
    ]

    if not card_payments.empty:

        missing_card_idx = (
            card_payments.sample(
                frac=0.002,
                random_state=503,
            ).index
        )

        df.loc[
            missing_card_idx,
            "card_id",
        ] = None

    # --------------------------------------------------
    # 4. Successful payment with failure reason - 0.1%
    # --------------------------------------------------

    successful_payments = df[
        df["payment_status"] == "SUCCESS"
    ]

    if not successful_payments.empty:

        invalid_failure_idx = (
            successful_payments.sample(
                frac=0.001,
                random_state=504,
            ).index
        )

        df.loc[
            invalid_failure_idx,
            "failure_reason",
        ] = "TIMEOUT"

    # --------------------------------------------------
    # 5. Failed payment without failure reason - 0.5%
    # --------------------------------------------------

    failed_payments = df[
        df["payment_status"] == "FAILED"
    ]

    if not failed_payments.empty:

        missing_failure_idx = (
            failed_payments.sample(
                frac=0.005,
                random_state=505,
            ).index
        )

        df.loc[
            missing_failure_idx,
            "failure_reason",
        ] = None

    # --------------------------------------------------
    # 6. Orphan Merchant - 0.1%
    # --------------------------------------------------

    orphan_merchant_idx = df.sample(
        frac=0.001,
        random_state=506,
    ).index

    for counter, idx in enumerate(
        orphan_merchant_idx,
        start=1,
    ):

        df.loc[
            idx,
            "merchant_id",
        ] = (
            f"MER_INVALID_{counter:05d}"
        )

    # --------------------------------------------------
    # 7. Duplicate payment events - 1%
    # --------------------------------------------------

    duplicate_rows = df.sample(
        frac=0.01,
        random_state=507,
    )

    df = pd.concat(
        [
            df,
            duplicate_rows,
        ],
        ignore_index=True,
    )

    return df


# --------------------------------------------------
# Main Execution
# --------------------------------------------------

if __name__ == "__main__":

    print()

    print("=" * 65)

    print(
        "FINTECH360 - PAYMENT SOURCE DATA GENERATION"
    )

    print("=" * 65)

    # --------------------------------------------------
    # Step 1: Load Parent Sources
    # --------------------------------------------------

    customers_df = pd.read_csv(
        CUSTOMER_FILE
    )

    accounts_df = pd.read_csv(
        ACCOUNT_FILE
    )

    cards_df = pd.read_csv(
        CARD_FILE
    )

    merchants_df = pd.read_csv(
        MERCHANT_FILE
    )

    # --------------------------------------------------
    # Step 2: Prepare Sources
    # --------------------------------------------------

    (
        customers_df,
        accounts_df,
        cards_df,
        merchants_df,
    ) = prepare_source_data(
        customers_df,
        accounts_df,
        cards_df,
        merchants_df,
    )

    # --------------------------------------------------
    # Step 3: Build Relationships
    # --------------------------------------------------

    (
        customer_accounts,
        account_cards,
    ) = build_lookups(
        accounts_df,
        cards_df,
    )

    # --------------------------------------------------
    # Step 4: Generate Valid Payments
    # --------------------------------------------------

    payments_df = generate_payments(
        num_payments=NUM_PAYMENTS,
        customers_df=customers_df,
        accounts_df=accounts_df,
        merchants_df=merchants_df,
        customer_accounts=customer_accounts,
        account_cards=account_cards,
    )

    base_payment_count = len(
        payments_df
    )

    # --------------------------------------------------
    # Step 5: Inject Source Problems
    # --------------------------------------------------

    payments_df = (
        inject_data_quality_issues(
            payments_df
        )
    )

    # --------------------------------------------------
    # Step 6: Save Raw Payments
    # --------------------------------------------------

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    payments_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print(
        f"Base payments generated: "
        f"{base_payment_count:,}"
    )

    print(
        f"Raw payment rows: "
        f"{len(payments_df):,}"
    )

    print(
        f"Unique payment IDs: "
        f"{payments_df['payment_id'].nunique():,}"
    )

    print(
        f"Duplicate payment IDs: "
        f"{payments_df['payment_id'].duplicated().sum():,}"
    )

    print(
        f"Successful payments: "
        f"{(
            payments_df['payment_status']
            == 'SUCCESS'
        ).sum():,}"
    )

    print(
        f"Failed payments: "
        f"{(
            payments_df['payment_status']
            == 'FAILED'
        ).sum():,}"
    )

    print(
        f"Negative payment amounts: "
        f"{(
            payments_df['amount'] < 0
        ).sum():,}"
    )

    print(
        f"CARD payments without card_id: "
        f"{(
            (
                payments_df['payment_method']
                == 'CARD'
            )
            & payments_df['card_id'].isna()
        ).sum():,}"
    )

    print(
        f"Successful payments with failure reason: "
        f"{(
            (
                payments_df['payment_status']
                == 'SUCCESS'
            )
            & payments_df[
                'failure_reason'
            ].notna()
        ).sum():,}"
    )

    print(
        f"Failed payments without failure reason: "
        f"{(
            (
                payments_df['payment_status']
                == 'FAILED'
            )
            & payments_df[
                'failure_reason'
            ].isna()
        ).sum():,}"
    )

    print(
        f"Orphan merchant IDs: "
        f"{payments_df[
            'merchant_id'
        ].astype(str).str.startswith(
            'MER_INVALID_'
        ).sum():,}"
    )

    print(
        f"Saved to: "
        f"{OUTPUT_FILE}"
    )

    print("=" * 65)

    print(
        "\nSample payment records:\n"
    )

    print(
        payments_df.head()
    )