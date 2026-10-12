import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


# --------------------------------------------------
# Configuration
# --------------------------------------------------

NUM_MERCHANTS = 5_000
RANDOM_SEED = 42

OUTPUT_DIRECTORY = Path(
    "sample_data/raw/merchants"
)

OUTPUT_FILE = OUTPUT_DIRECTORY / "merchants.csv"

fake = Faker("en_IN")

Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


# --------------------------------------------------
# Business Reference Data
# --------------------------------------------------

STATES_AND_CITIES = {
    "Telangana": ["Hyderabad", "Warangal"],
    "Karnataka": ["Bengaluru", "Mysore"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Salem", "Madurai"],
    "Delhi": ["New Delhi"],
    "Gujarat": ["Ahmedabad", "Surat"],
    "Kerala": ["Kochi", "Kozhikode", "Thiruvananthapuram"],
    "West Bengal": ["Kolkata"],
    "Uttar Pradesh": ["Noida", "Lucknow"],
    "Rajasthan": ["Jaipur"],
}


MERCHANT_CATEGORIES = {
    "GROCERY": "5411",
    "RESTAURANT": "5812",
    "ECOMMERCE": "5969",
    "TRAVEL": "4722",
    "FUEL": "5541",
    "ENTERTAINMENT": "7832",
    "HEALTHCARE": "8099",
    "EDUCATION": "8299",
    "ELECTRONICS": "5732",
    "FASHION": "5699",
    "UTILITIES": "4900",
}


MERCHANT_SIZES = [
    "SMALL",
    "MEDIUM",
    "LARGE",
]


MERCHANT_STATUSES = [
    "ACTIVE",
    "INACTIVE",
    "SUSPENDED",
]


RISK_RATINGS = [
    "LOW",
    "MEDIUM",
    "HIGH",
]


# --------------------------------------------------
# Generate One Merchant
# --------------------------------------------------

def generate_merchant(
    merchant_number: int
) -> dict:

    merchant_id = (
        f"MER{merchant_number:06d}"
    )

    state = random.choice(
        list(
            STATES_AND_CITIES.keys()
        )
    )

    city = random.choice(
        STATES_AND_CITIES[state]
    )

    merchant_category = random.choice(
        list(
            MERCHANT_CATEGORIES.keys()
        )
    )

    mcc_code = MERCHANT_CATEGORIES[
        merchant_category
    ]

    onboarding_date = fake.date_between(
        start_date="-5y",
        end_date="today"
    )

    onboarding_datetime = datetime.combine(
        onboarding_date,
        datetime.min.time()
    )

    days_since_onboarding = (
        datetime.now()
        - onboarding_datetime
    ).days

    updated_at = (
        onboarding_datetime
        + timedelta(
            days=random.randint(
                0,
                max(
                    days_since_onboarding,
                    0
                )
            )
        )
    )

    return {
        "merchant_id": merchant_id,

        "merchant_name": (
            fake.company()
        ),

        "merchant_category": (
            merchant_category
        ),

        "mcc_code": mcc_code,

        "city": city,

        "state": state,

        "postal_code": (
            fake.postcode()
        ),

        "merchant_size": random.choices(
            MERCHANT_SIZES,
            weights=[65, 25, 10],
            k=1
        )[0],

        "onboarding_date": (
            onboarding_date
        ),

        "merchant_status": (
            random.choices(
                MERCHANT_STATUSES,
                weights=[92, 5, 3],
                k=1
            )[0]
        ),

        "risk_rating": (
            random.choices(
                RISK_RATINGS,
                weights=[75, 20, 5],
                k=1
            )[0]
        ),

        "created_at": (
            onboarding_datetime
        ),

        "updated_at": (
            updated_at
        ),
    }


# --------------------------------------------------
# Generate Merchant Dataset
# --------------------------------------------------

def generate_merchants(
    num_merchants: int
) -> pd.DataFrame:

    merchants = [
        generate_merchant(i)
        for i in range(
            1,
            num_merchants + 1
        )
    ]

    return pd.DataFrame(
        merchants
    )


# --------------------------------------------------
# Inject Controlled Data Quality Problems
# --------------------------------------------------

def inject_data_quality_issues(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    # --------------------------------------------------
    # 1. Missing Merchant Name - 0.5%
    # --------------------------------------------------

    missing_name_idx = df.sample(
        frac=0.005,
        random_state=401
    ).index

    df.loc[
        missing_name_idx,
        "merchant_name"
    ] = None


    # --------------------------------------------------
    # 2. Invalid MCC Code - 0.3%
    # --------------------------------------------------

    invalid_mcc_idx = df.sample(
        frac=0.003,
        random_state=402
    ).index

    df.loc[
        invalid_mcc_idx,
        "mcc_code"
    ] = "9999"


    # --------------------------------------------------
    # 3. Inconsistent City Formatting - 1%
    # --------------------------------------------------

    city_issue_idx = df.sample(
        frac=0.01,
        random_state=403
    ).index

    df.loc[
        city_issue_idx,
        "city"
    ] = (
        " "
        + df.loc[
            city_issue_idx,
            "city"
        ].str.upper()
        + " "
    )


    # --------------------------------------------------
    # 4. Invalid Merchant Status - 0.2%
    # --------------------------------------------------

    invalid_status_idx = df.sample(
        frac=0.002,
        random_state=404
    ).index

    df.loc[
        invalid_status_idx,
        "merchant_status"
    ] = "UNKNOWN"


    # --------------------------------------------------
    # 5. Duplicate Merchant Records - 1%
    # --------------------------------------------------

    duplicate_rows = df.sample(
        frac=0.01,
        random_state=405
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
        "FINTECH360 - MERCHANT SOURCE DATA GENERATION"
    )

    print("=" * 60)

    # ----------------------------------------------
    # Step 1: Generate valid merchants
    # ----------------------------------------------

    merchants_df = generate_merchants(
        NUM_MERCHANTS
    )

    base_merchant_count = len(
        merchants_df
    )

    # ----------------------------------------------
    # Step 2: Inject source problems
    # ----------------------------------------------

    merchants_df = (
        inject_data_quality_issues(
            merchants_df
        )
    )

    # ----------------------------------------------
    # Step 3: Create output directory
    # ----------------------------------------------

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    # ----------------------------------------------
    # Step 4: Save raw merchant data
    # ----------------------------------------------

    merchants_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ----------------------------------------------
    # Summary
    # ----------------------------------------------

    print(
        f"Base merchants generated: "
        f"{base_merchant_count:,}"
    )

    print(
        f"Raw merchant rows: "
        f"{len(merchants_df):,}"
    )

    print(
        f"Unique merchant IDs: "
        f"{merchants_df['merchant_id'].nunique():,}"
    )

    print(
        f"Duplicate merchant IDs: "
        f"{merchants_df['merchant_id'].duplicated().sum():,}"
    )

    print(
        f"Missing merchant names: "
        f"{merchants_df['merchant_name'].isna().sum():,}"
    )

    print(
        f"Invalid MCC codes: "
        f"{(merchants_df['mcc_code'] == '9999').sum():,}"
    )

    print(
        f"Invalid merchant statuses: "
        f"{(merchants_df['merchant_status'] == 'UNKNOWN').sum():,}"
    )

    print(
        f"Saved to: "
        f"{OUTPUT_FILE}"
    )

    print("=" * 60)

    print(
        "\nSample records:\n"
    )

    print(
        merchants_df.head()
    )