import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


# --------------------------------------------------
# Configuration
# --------------------------------------------------

NUM_CUSTOMERS = 10_000
RANDOM_SEED = 42

fake = Faker("en_IN")

# Make synthetic data reproducible
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

OCCUPATIONS = [
    "Software Engineer",
    "Data Analyst",
    "Accountant",
    "Teacher",
    "Doctor",
    "Sales Executive",
    "Business Owner",
    "Consultant",
    "Operations Executive",
    "Student",
]

KYC_STATUSES = [
    "VERIFIED",
    "PENDING",
    "REJECTED",
]

RISK_RATINGS = [
    "LOW",
    "MEDIUM",
    "HIGH",
]

CUSTOMER_STATUSES = [
    "ACTIVE",
    "INACTIVE",
    "SUSPENDED",
]


# --------------------------------------------------
# Generate One Valid Customer
# --------------------------------------------------

def generate_customer(customer_number: int) -> dict:
    """
    Generate one valid synthetic FinTech360 customer.
    """

    customer_id = f"CUST{customer_number:06d}"

    # Select state first so that city belongs to the selected state
    state = random.choice(list(STATES_AND_CITIES.keys()))
    city = random.choice(STATES_AND_CITIES[state])

    # Generate DOB for customers aged 18-75
    date_of_birth = fake.date_of_birth(
        minimum_age=18,
        maximum_age=75
    )

    # Customer registration can be anytime during the last 5 years
    registration_date = fake.date_between(
        start_date="-5y",
        end_date="today"
    )

    # Convert registration date to datetime
    registration_datetime = datetime.combine(
        registration_date,
        datetime.min.time()
    )

    # updated_at must not be earlier than registration
    # or later than the current date
    days_since_registration = (
        datetime.now() - registration_datetime
    ).days

    updated_at = registration_datetime + timedelta(
        days=random.randint(
            0,
            max(days_since_registration, 0)
        )
    )

    return {
        "customer_id": customer_id,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "date_of_birth": date_of_birth,
        "gender": random.choice(
            ["M", "F", "OTHER"]
        ),
        "email": fake.email(),
        "mobile_number": fake.msisdn()[:10],
        "city": city,
        "state": state,
        "postal_code": fake.postcode(),
        "occupation": random.choice(
            OCCUPATIONS
        ),
        "annual_income": random.randint(
            200_000,
            5_000_000
        ),
        "kyc_status": random.choices(
            KYC_STATUSES,
            weights=[90, 7, 3],
            k=1
        )[0],
        "risk_rating": random.choices(
            RISK_RATINGS,
            weights=[70, 25, 5],
            k=1
        )[0],
        "registration_date": registration_date,
        "customer_status": random.choices(
            CUSTOMER_STATUSES,
            weights=[90, 7, 3],
            k=1
        )[0],
        "updated_at": updated_at,
    }


# --------------------------------------------------
# Generate Valid Customer Dataset
# --------------------------------------------------

def generate_customers(
    num_customers: int
) -> pd.DataFrame:
    """
    Generate the valid baseline customer dataset.
    """

    customers = [
        generate_customer(i)
        for i in range(
            1,
            num_customers + 1
        )
    ]

    return pd.DataFrame(customers)


# --------------------------------------------------
# Inject Controlled Data Quality Problems
# --------------------------------------------------

def inject_data_quality_issues(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Introduce controlled data-quality problems
    to simulate imperfect operational source data.
    """

    df = df.copy()

    # --------------------------------------------------
    # 1. Missing Email Addresses - 1%
    # --------------------------------------------------

    missing_email_idx = df.sample(
        frac=0.01,
        random_state=101
    ).index

    df.loc[
        missing_email_idx,
        "email"
    ] = None


    # --------------------------------------------------
    # 2. Invalid Annual Income - 0.5%
    # --------------------------------------------------

    invalid_income_idx = df.sample(
        frac=0.005,
        random_state=102
    ).index

    df.loc[
        invalid_income_idx,
        "annual_income"
    ] = -50_000


    # --------------------------------------------------
    # 3. Inconsistent City Formatting - 1%
    # --------------------------------------------------

    city_issue_idx = df.sample(
        frac=0.01,
        random_state=103
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
    # 4. Invalid KYC Status - 0.5%
    # --------------------------------------------------

    invalid_kyc_idx = df.sample(
        frac=0.005,
        random_state=104
    ).index

    df.loc[
        invalid_kyc_idx,
        "kyc_status"
    ] = "UNKNOWN"


    # --------------------------------------------------
    # 5. Duplicate Customer Records - 2%
    # --------------------------------------------------

    duplicate_rows = df.sample(
        frac=0.02,
        random_state=105
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

    # Step 1:
    # Generate valid baseline customers
    df = generate_customers(
        NUM_CUSTOMERS
    )

    # Step 2:
    # Introduce controlled source-data problems
    df = inject_data_quality_issues(
        df
    )

    # Step 3:
    # Define raw landing directory
    output_directory = Path(
        "sample_data/raw/customers"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    # Step 4:
    # Define output file
    output_file = (
        output_directory
        / "customers.csv"
    )

    # Step 5:
    # Write raw customer data
    df.to_csv(
        output_file,
        index=False
    )

    # --------------------------------------------------
    # Source Data Summary
    # --------------------------------------------------

    print("\n")
    print("=" * 60)
    print("FINTECH360 - CUSTOMER SOURCE DATA GENERATION")
    print("=" * 60)

    print(
        f"Base customers generated: "
        f"{NUM_CUSTOMERS:,}"
    )

    print(
        f"Raw source rows after issue injection: "
        f"{len(df):,}"
    )

    print(
        f"Unique customers: "
        f"{df['customer_id'].nunique():,}"
    )

    print(
        f"Duplicate customer IDs: "
        f"{df['customer_id'].duplicated().sum():,}"
    )

    print(
        f"Missing emails: "
        f"{df['email'].isna().sum():,}"
    )

    print(
        f"Invalid incomes: "
        f"{(df['annual_income'] < 0).sum():,}"
    )

    print(
        f"Invalid KYC statuses: "
        f"{(df['kyc_status'] == 'UNKNOWN').sum():,}"
    )

    print("-" * 60)

    print(
        f"Raw source file saved to: "
        f"{output_file}"
    )

    print("=" * 60)

    print("\nSample records:\n")

    print(
        df.head()
    )