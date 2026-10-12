import random
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

RANDOM_SEED = 42

PAYMENT_FILE = Path(
    "sample_data/raw/payments/payments.csv"
)

ACCOUNT_FILE = Path(
    "sample_data/raw/accounts/accounts.csv"
)

OUTPUT_DIRECTORY = Path(
    "sample_data/raw/transactions"
)

OUTPUT_FILE = OUTPUT_DIRECTORY / "transactions.csv"

random.seed(RANDOM_SEED)


# --------------------------------------------------
# Generate Transactions From Successful Payments
# --------------------------------------------------

def generate_payment_transactions(
    payments_df: pd.DataFrame,
    account_balances: dict,
    starting_transaction_number: int = 1
):

    transactions = []

    transaction_number = (
        starting_transaction_number
    )

    successful_payments = payments_df[
        payments_df["payment_status"] == "SUCCESS"
    ].copy()

    for _, payment in successful_payments.iterrows():

        account_id = payment["account_id"]

        # Skip if account does not exist
        if account_id not in account_balances:
            continue

        amount = float(
            payment["amount"]
        )

        # Skip invalid negative/zero source amounts.
        # These remain in raw payments for later DQ testing.
        if amount <= 0:
            continue

        balance_before = (
            account_balances[account_id]
        )

        balance_after = (
            balance_before - amount
        )

        transaction_id = (
            f"TXN{transaction_number:010d}"
        )

        transactions.append(
            {
                "transaction_id": transaction_id,
                "account_id": account_id,
                "payment_id": payment["payment_id"],
                "transaction_type": "DEBIT",
                "transaction_category": "MERCHANT_PAYMENT",
                "amount": amount,
                "currency": payment["currency"],
                "balance_before": round(
                    balance_before,
                    2
                ),
                "balance_after": round(
                    balance_after,
                    2
                ),
                "transaction_status": "POSTED",
                "transaction_timestamp": payment[
                    "payment_timestamp"
                ],
                "created_at": payment[
                    "payment_timestamp"
                ],
            }
        )

        account_balances[
            account_id
        ] = balance_after

        transaction_number += 1

    return (
        transactions,
        transaction_number
    )


# --------------------------------------------------
# Generate Non-Payment Ledger Transactions
# --------------------------------------------------

def generate_non_payment_transactions(
    accounts_df: pd.DataFrame,
    account_balances: dict,
    transaction_number: int,
    number_of_transactions: int
):

    transactions = []

    account_ids = (
        accounts_df["account_id"]
        .dropna()
        .unique()
        .tolist()
    )

    categories = [
        "CASHBACK",
        "FEE",
        "TOPUP",
        "WITHDRAWAL",
    ]

    category_weights = [
        30,
        20,
        35,
        15,
    ]

    for _ in range(
        number_of_transactions
    ):

        account_id = random.choice(
            account_ids
        )

        category = random.choices(
            categories,
            weights=category_weights,
            k=1
        )[0]

        # ------------------------------------------
        # Determine transaction direction
        # ------------------------------------------

        if category in [
            "CASHBACK",
            "TOPUP",
        ]:

            transaction_type = "CREDIT"

        else:

            transaction_type = "DEBIT"

        # ------------------------------------------
        # Generate realistic amount range
        # ------------------------------------------

        if category == "CASHBACK":

            amount = round(
                random.uniform(
                    10,
                    500
                ),
                2
            )

        elif category == "FEE":

            amount = round(
                random.uniform(
                    10,
                    1_000
                ),
                2
            )

        elif category == "TOPUP":

            amount = round(
                random.uniform(
                    100,
                    50_000
                ),
                2
            )

        else:

            amount = round(
                random.uniform(
                    100,
                    20_000
                ),
                2
            )

        balance_before = (
            account_balances[
                account_id
            ]
        )

        if transaction_type == "CREDIT":

            balance_after = (
                balance_before + amount
            )

        else:

            balance_after = (
                balance_before - amount
            )

        transaction_id = (
            f"TXN{transaction_number:010d}"
        )

        # Generate a timestamp during
        # the last 12 months.
        transaction_timestamp = (
            pd.Timestamp.now()
            - pd.Timedelta(
                days=random.randint(
                    0,
                    365
                ),
                hours=random.randint(
                    0,
                    23
                ),
                minutes=random.randint(
                    0,
                    59
                )
            )
        )

        transactions.append(
            {
                "transaction_id": transaction_id,
                "account_id": account_id,

                # Important:
                # This transaction was not created
                # by a payment attempt.
                "payment_id": None,

                "transaction_type": (
                    transaction_type
                ),

                "transaction_category": (
                    category
                ),

                "amount": amount,
                "currency": "INR",

                "balance_before": round(
                    balance_before,
                    2
                ),

                "balance_after": round(
                    balance_after,
                    2
                ),

                "transaction_status": "POSTED",

                "transaction_timestamp": (
                    transaction_timestamp
                ),

                "created_at": (
                    transaction_timestamp
                ),
            }
        )

        account_balances[
            account_id
        ] = balance_after

        transaction_number += 1

    return transactions


# --------------------------------------------------
# Inject Controlled Data Quality Issues
# --------------------------------------------------

def inject_data_quality_issues(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    # --------------------------------------------------
    # 1. Negative transaction amount - 0.2%
    # --------------------------------------------------

    invalid_amount_idx = df.sample(
        frac=0.002,
        random_state=601
    ).index

    df.loc[
        invalid_amount_idx,
        "amount"
    ] = -500


    # --------------------------------------------------
    # 2. Invalid transaction type - 0.1%
    # --------------------------------------------------

    invalid_type_idx = df.sample(
        frac=0.001,
        random_state=602
    ).index

    df.loc[
        invalid_type_idx,
        "transaction_type"
    ] = "UNKNOWN"


    # --------------------------------------------------
    # 3. Invalid transaction status - 0.1%
    # --------------------------------------------------

    invalid_status_idx = df.sample(
        frac=0.001,
        random_state=603
    ).index

    df.loc[
        invalid_status_idx,
        "transaction_status"
    ] = "INVALID"


    # --------------------------------------------------
    # 4. Incorrect balance calculation - 0.2%
    # --------------------------------------------------

    invalid_balance_idx = df.sample(
        frac=0.002,
        random_state=604
    ).index

    df.loc[
        invalid_balance_idx,
        "balance_after"
    ] = (
        df.loc[
            invalid_balance_idx,
            "balance_after"
        ]
        + 999
    )


    # --------------------------------------------------
    # 5. Orphan Account IDs - 0.1%
    # --------------------------------------------------

    orphan_account_idx = df.sample(
        frac=0.001,
        random_state=605
    ).index

    for counter, idx in enumerate(
        orphan_account_idx,
        start=1
    ):

        df.loc[
            idx,
            "account_id"
        ] = (
            f"ACC_INVALID_TXN_{counter:05d}"
        )


    # --------------------------------------------------
    # 6. Duplicate transaction events - 1%
    # --------------------------------------------------

    duplicate_rows = df.sample(
        frac=0.01,
        random_state=606
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

    print("=" * 65)
    print(
        "FINTECH360 - TRANSACTION SOURCE DATA GENERATION"
    )
    print("=" * 65)

    # --------------------------------------------------
    # Step 1: Load Payment Source
    # --------------------------------------------------

    payments_df = pd.read_csv(
        PAYMENT_FILE
    )

    # Remove duplicated payment events only for
    # generation of downstream synthetic records.
    payments_df = (
        payments_df
        .drop_duplicates(
            subset=["payment_id"]
        )
        .copy()
    )

    # --------------------------------------------------
    # Step 2: Load Account Source
    # --------------------------------------------------

    accounts_df = pd.read_csv(
        ACCOUNT_FILE
    )

    accounts_df = (
        accounts_df
        .drop_duplicates(
            subset=["account_id"]
        )
        .copy()
    )

    # Remove deliberately corrupted account records
    # from our relationship-generation source.
    accounts_df = accounts_df[
        ~accounts_df["account_id"]
        .astype(str)
        .str.startswith("ACC_INVALID")
    ].copy()

    # --------------------------------------------------
    # Step 3: Initialize Ledger Balances
    # --------------------------------------------------

    account_balances = dict(
        zip(
            accounts_df["account_id"],
            accounts_df[
                "current_balance"
            ].astype(float)
        )
    )

    # --------------------------------------------------
    # Step 4: Generate Payment Transactions
    # --------------------------------------------------

    (
        payment_transactions,
        next_transaction_number
    ) = generate_payment_transactions(
        payments_df=payments_df,
        account_balances=account_balances,
        starting_transaction_number=1,
    )

    print(
        f"Transactions generated from "
        f"successful payments: "
        f"{len(payment_transactions):,}"
    )

    # --------------------------------------------------
    # Step 5: Generate Additional Ledger Activity
    # --------------------------------------------------

    # Generate approximately 20% additional
    # non-payment ledger transactions.
    number_of_non_payment_transactions = int(
        len(payment_transactions)
        * 0.20
    )

    non_payment_transactions = (
        generate_non_payment_transactions(
            accounts_df=accounts_df,
            account_balances=account_balances,
            transaction_number=(
                next_transaction_number
            ),
            number_of_transactions=(
                number_of_non_payment_transactions
            ),
        )
    )

    print(
        f"Non-payment transactions generated: "
        f"{len(non_payment_transactions):,}"
    )

    # --------------------------------------------------
    # Step 6: Combine Ledger Events
    # --------------------------------------------------

    all_transactions = (
        payment_transactions
        + non_payment_transactions
    )

    transactions_df = pd.DataFrame(
        all_transactions
    )

    base_transaction_count = len(
        transactions_df
    )

    # --------------------------------------------------
    # Step 7: Inject Source Problems
    # --------------------------------------------------

    transactions_df = (
        inject_data_quality_issues(
            transactions_df
        )
    )

    # --------------------------------------------------
    # Step 8: Save Raw Transaction Source
    # --------------------------------------------------

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    transactions_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print("-" * 65)

    print(
        f"Base transactions generated: "
        f"{base_transaction_count:,}"
    )

    print(
        f"Raw transaction rows: "
        f"{len(transactions_df):,}"
    )

    print(
        f"Unique transaction IDs: "
        f"{transactions_df['transaction_id'].nunique():,}"
    )

    print(
        f"Duplicate transaction IDs: "
        f"{transactions_df['transaction_id'].duplicated().sum():,}"
    )

    print(
        f"Payment-linked transactions: "
        f"{transactions_df['payment_id'].notna().sum():,}"
    )

    print(
        f"Non-payment transactions: "
        f"{transactions_df['payment_id'].isna().sum():,}"
    )

    print(
        f"Negative transaction amounts: "
        f"{(transactions_df['amount'] < 0).sum():,}"
    )

    print(
        f"Invalid transaction types: "
        f"{(transactions_df['transaction_type'] == 'UNKNOWN').sum():,}"
    )

    print(
        f"Invalid transaction statuses: "
        f"{(transactions_df['transaction_status'] == 'INVALID').sum():,}"
    )

    print(
        f"Orphan account IDs: "
        f"{transactions_df['account_id'].astype(str).str.startswith('ACC_INVALID_TXN_').sum():,}"
    )

    print(
        f"Saved to: "
        f"{OUTPUT_FILE}"
    )

    print("=" * 65)

    print(
        "\nSample transaction records:\n"
    )

    print(
        transactions_df.head()
    )