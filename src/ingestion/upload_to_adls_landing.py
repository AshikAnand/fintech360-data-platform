from datetime import datetime
from pathlib import Path

from azure.core.exceptions import (
    ResourceExistsError,
    ResourceNotFoundError,
)
from azure.identity import AzureCliCredential
from azure.storage.filedatalake import DataLakeServiceClient


# ============================================================
# FINTECH360 - ADLS LANDING DELIVERY
# ============================================================

STORAGE_ACCOUNT_NAME = "stfintech360devashik"
FILE_SYSTEM_NAME = "landing"

STORAGE_ACCOUNT_URL = (
    f"https://{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_ROOT = PROJECT_ROOT / "sample_data" / "raw"

BATCH_NUMBER = 1

# 4 MB chunks
CHUNK_SIZE = 4 * 1024 * 1024


# ============================================================
# SOURCE FILE CONFIGURATION
# ============================================================

SOURCE_FILES = {
    "customers": RAW_ROOT / "customers" / "customers.csv",
    "accounts": RAW_ROOT / "accounts" / "accounts.csv",
    "cards": RAW_ROOT / "cards" / "cards.csv",
    "merchants": RAW_ROOT / "merchants" / "merchants.csv",
    "payments": RAW_ROOT / "payments" / "payments.csv",
    "transactions": RAW_ROOT / "transactions" / "transactions.csv",
    "products": RAW_ROOT / "products" / "products.csv",
    "customer_products": (
        RAW_ROOT
        / "customer_products"
        / "customer_products.csv"
    ),
}


# ============================================================
# AZURE CONNECTION
# ============================================================

def get_file_system_client():
    """
    Authenticate using the Azure CLI Microsoft Entra session.

    No storage account keys, SAS tokens, passwords or secrets
    are stored in the project.
    """

    credential = AzureCliCredential()

    service_client = DataLakeServiceClient(
        account_url=STORAGE_ACCOUNT_URL,
        credential=credential,
    )

    return service_client.get_file_system_client(
        file_system=FILE_SYSTEM_NAME
    )


# ============================================================
# VALIDATE LOCAL SOURCES
# ============================================================

def validate_local_sources():
    """
    Confirm that all expected source-system simulator files
    exist before beginning the landing delivery.
    """

    print()
    print("Validating local source files...")
    print("-" * 70)

    missing_files = []

    for entity_name, local_file in SOURCE_FILES.items():

        if local_file.exists():

            file_size_mb = (
                local_file.stat().st_size
                / (1024 * 1024)
            )

            print(
                f"[FOUND]   "
                f"{entity_name:<20} "
                f"{file_size_mb:>8.2f} MB"
            )

        else:

            print(
                f"[MISSING] "
                f"{entity_name:<20} "
                f"{local_file}"
            )

            missing_files.append(local_file)

    print("-" * 70)

    if missing_files:

        raise FileNotFoundError(
            "One or more required source files are missing. "
            "Landing delivery stopped."
        )

    print(
        "All expected local source files are available."
    )


# ============================================================
# BUILD LANDING PATH
# ============================================================

def build_landing_paths(
    entity_name,
    delivery_date,
    batch_number,
):
    """
    Build a date-partitioned landing path.

    Example:

    accounts/2026/10/12/accounts_20261012_001.csv
    """

    year = delivery_date.strftime("%Y")
    month = delivery_date.strftime("%m")
    day = delivery_date.strftime("%d")

    date_string = delivery_date.strftime("%Y%m%d")

    directory_path = (
        f"{entity_name}/"
        f"{year}/"
        f"{month}/"
        f"{day}"
    )

    destination_file_name = (
        f"{entity_name}_"
        f"{date_string}_"
        f"{batch_number:03d}.csv"
    )

    destination_path = (
        f"{directory_path}/"
        f"{destination_file_name}"
    )

    return directory_path, destination_path


# ============================================================
# CREATE DIRECTORY HIERARCHY
# ============================================================

def ensure_directory_exists(
    file_system_client,
    directory_path,
):
    """
    Create the ADLS hierarchy one level at a time.

    Example:

    payments
    payments/2026
    payments/2026/10
    payments/2026/10/12
    """

    path_parts = directory_path.split("/")

    current_path = ""

    for part in path_parts:

        if current_path:
            current_path = f"{current_path}/{part}"
        else:
            current_path = part

        directory_client = (
            file_system_client.get_directory_client(
                current_path
            )
        )

        try:

            directory_client.create_directory()

        except ResourceExistsError:

            # Expected during reruns.
            pass


# ============================================================
# CHECK DESTINATION FILE
# ============================================================

def destination_file_exists(
    file_system_client,
    destination_path,
):
    """
    Return True if the exact landing batch already exists.
    """

    file_client = (
        file_system_client.get_file_client(
            destination_path
        )
    )

    try:

        file_client.get_file_properties()

        return True

    except ResourceNotFoundError:

        return False


# ============================================================
# VERIFY UPLOADED FILE
# ============================================================

def verify_uploaded_file(
    file_system_client,
    destination_path,
    expected_size,
):
    """
    Verify that the uploaded ADLS file size matches
    the local source file size.
    """

    file_client = (
        file_system_client.get_file_client(
            destination_path
        )
    )

    properties = file_client.get_file_properties()

    cloud_size = properties.size

    if cloud_size != expected_size:

        raise RuntimeError(
            "Upload verification failed. "
            f"Local size={expected_size} bytes, "
            f"ADLS size={cloud_size} bytes."
        )

    return cloud_size


# ============================================================
# CHUNKED FILE UPLOAD
# ============================================================

def upload_file_in_chunks(
    file_system_client,
    local_file,
    destination_path,
):
    """
    Upload a local file using explicit ADLS operations:

        create_file()
            ↓
        append_data()
            ↓
        append_data()
            ↓
        ...
            ↓
        flush_data()

    Files are read in chunks instead of loading the
    complete file into memory.
    """

    file_client = (
        file_system_client.get_file_client(
            destination_path
        )
    )

    # Create an empty ADLS file.
    file_client.create_file()

    offset = 0

    try:

        with open(local_file, "rb") as source_file:

            while True:

                chunk = source_file.read(
                    CHUNK_SIZE
                )

                if not chunk:
                    break

                file_client.append_data(
                    data=chunk,
                    offset=offset,
                    length=len(chunk),
                )

                offset += len(chunk)

        # Commit the uploaded bytes.
        file_client.flush_data(offset)

    except Exception:

        # A partially-created file should not remain
        # and incorrectly appear as a completed batch.
        try:
            file_client.delete_file()
        except Exception:
            pass

        raise

    return offset


# ============================================================
# UPLOAD ONE SOURCE DATASET
# ============================================================

def upload_source_file(
    file_system_client,
    entity_name,
    local_file,
    delivery_date,
    batch_number,
):
    """
    Deliver one source-system extract into the
    ADLS landing zone.
    """

    if not local_file.exists():

        raise FileNotFoundError(
            f"Source file not found: {local_file}"
        )

    directory_path, destination_path = (
        build_landing_paths(
            entity_name=entity_name,
            delivery_date=delivery_date,
            batch_number=batch_number,
        )
    )

    # --------------------------------------------------------
    # 1. Ensure directory hierarchy exists
    # --------------------------------------------------------

    ensure_directory_exists(
        file_system_client=file_system_client,
        directory_path=directory_path,
    )

    # --------------------------------------------------------
    # 2. Idempotency check
    # --------------------------------------------------------

    if destination_file_exists(
        file_system_client=file_system_client,
        destination_path=destination_path,
    ):

        return {
            "status": "ALREADY_EXISTS",
            "entity": entity_name,
            "destination_path": destination_path,
            "size": None,
        }

    # --------------------------------------------------------
    # 3. Upload
    # --------------------------------------------------------

    local_size = local_file.stat().st_size

    uploaded_size = upload_file_in_chunks(
        file_system_client=file_system_client,
        local_file=local_file,
        destination_path=destination_path,
    )

    # --------------------------------------------------------
    # 4. Verify
    # --------------------------------------------------------

    cloud_size = verify_uploaded_file(
        file_system_client=file_system_client,
        destination_path=destination_path,
        expected_size=local_size,
    )

    if uploaded_size != local_size:

        raise RuntimeError(
            f"Byte count mismatch for {entity_name}. "
            f"Uploaded={uploaded_size}, "
            f"Local={local_size}"
        )

    return {
        "status": "UPLOADED",
        "entity": entity_name,
        "destination_path": destination_path,
        "size": cloud_size,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("FINTECH360 - ADLS LANDING DELIVERY")
    print("=" * 70)

    delivery_date = datetime.now()

    batch_number = BATCH_NUMBER

    print(
        f"Storage account : {STORAGE_ACCOUNT_NAME}"
    )

    print(
        f"File system     : {FILE_SYSTEM_NAME}"
    )

    print(
        "Delivery date   : "
        f"{delivery_date.strftime('%Y-%m-%d')}"
    )

    print(
        f"Batch number    : {batch_number:03d}"
    )

    # ========================================================
    # STEP 1 - LOCAL VALIDATION
    # ========================================================

    validate_local_sources()

    # ========================================================
    # STEP 2 - CONNECT TO ADLS
    # ========================================================

    print()
    print("Connecting to ADLS Gen2...")
    print("-" * 70)

    try:

        file_system_client = (
            get_file_system_client()
        )

        # Force an authenticated API call.
        (
            file_system_client
            .get_file_system_properties()
        )

        print(
            "[OK] Connected to ADLS Gen2 "
            "using Microsoft Entra authentication."
        )

    except Exception as exc:

        print(
            "[ERROR] Unable to connect "
            "to ADLS Gen2."
        )

        print(
            f"Reason: {exc}"
        )

        raise

    # ========================================================
    # STEP 3 - LAND SOURCE FILES
    # ========================================================

    print()
    print("Uploading source delivery batch...")
    print("-" * 70)

    uploaded_count = 0
    existing_count = 0
    failed_count = 0

    for entity_name, local_file in SOURCE_FILES.items():

        try:

            result = upload_source_file(
                file_system_client=(
                    file_system_client
                ),
                entity_name=entity_name,
                local_file=local_file,
                delivery_date=delivery_date,
                batch_number=batch_number,
            )

            if result["status"] == "UPLOADED":

                uploaded_count += 1

                size_mb = (
                    result["size"]
                    / (1024 * 1024)
                )

                print(
                    f"[UPLOADED]       "
                    f"{entity_name:<20} "
                    f"{size_mb:>8.2f} MB "
                    f"-> "
                    f"{result['destination_path']}"
                )

            elif (
                result["status"]
                == "ALREADY_EXISTS"
            ):

                existing_count += 1

                print(
                    f"[ALREADY EXISTS] "
                    f"{entity_name:<20} "
                    f"-> "
                    f"{result['destination_path']}"
                )

        except Exception as exc:

            failed_count += 1

            print(
                f"[FAILED]         "
                f"{entity_name:<20} "
                f"-> {exc}"
            )

    # ========================================================
    # STEP 4 - SUMMARY
    # ========================================================

    print("-" * 70)

    print(
        f"Total source datasets : "
        f"{len(SOURCE_FILES)}"
    )

    print(
        f"Uploaded              : "
        f"{uploaded_count}"
    )

    print(
        f"Already existed       : "
        f"{existing_count}"
    )

    print(
        f"Failed                : "
        f"{failed_count}"
    )

    print("-" * 70)

    if failed_count == 0:

        print(
            "LANDING DELIVERY COMPLETED SUCCESSFULLY"
        )

    else:

        print(
            "LANDING DELIVERY COMPLETED WITH ERRORS"
        )

    print("=" * 70)