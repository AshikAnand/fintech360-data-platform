# FinTech360 — ADLS Landing Zone Ingestion

## 1. Purpose

The FinTech360 Landing Zone is the first cloud layer of the data platform.

Its responsibility is to receive source-system extracts and preserve them as immutable delivery files before Databricks processing begins.

The Landing Zone is intentionally separate from Bronze.

```text
Simulated Operational Sources
            |
            v
Local Raw Extracts
            |
            v
ADLS Gen2 Landing
            |
            v
Databricks Bronze
```

The landing process is implemented in:

`src/ingestion/upload_to_adls_landing.py`


## 2. Source Datasets

The first FinTech360 delivery contains eight interconnected datasets:

| Dataset | Source File |
|---|---|
| customers | `sample_data/raw/customers/customers.csv` |
| accounts | `sample_data/raw/accounts/accounts.csv` |
| cards | `sample_data/raw/cards/cards.csv` |
| merchants | `sample_data/raw/merchants/merchants.csv` |
| payments | `sample_data/raw/payments/payments.csv` |
| transactions | `sample_data/raw/transactions/transactions.csv` |
| products | `sample_data/raw/products/products.csv` |
| customer_products | `sample_data/raw/customer_products/customer_products.csv` |

These files are outputs of the FinTech360 source-system simulator.

They are not Bronze tables and are not intended to represent the final analytical storage format.


## 3. Landing Filesystem

The Azure Data Lake Storage Gen2 filesystem is:

`landing`

Each source receives its own directory.

Deliveries are partitioned by delivery date:

```text
landing/
├── customers/YYYY/MM/DD/
├── accounts/YYYY/MM/DD/
├── cards/YYYY/MM/DD/
├── merchants/YYYY/MM/DD/
├── payments/YYYY/MM/DD/
├── transactions/YYYY/MM/DD/
├── products/YYYY/MM/DD/
└── customer_products/YYYY/MM/DD/
```

The naming convention is:

```text
<entity>_YYYYMMDD_<batch_number>.csv
```

Example:

```text
payments/2026/10/12/payments_20261012_001.csv
```


## 4. Why Date-Based Delivery Paths?

A source file is not repeatedly overwritten using a fixed name such as:

```text
payments.csv
```

Instead, every delivery belongs to a specific date and batch.

This design provides a foundation for:

- Historical retention
- Incremental ingestion
- Replay
- Auditability
- Multiple daily batches
- Failure recovery
- Databricks Auto Loader
- Operational troubleshooting

For example, future deliveries could look like:

```text
payments/
├── 2026/
│   └── 10/
│       ├── 12/
│       │   ├── payments_20261012_001.csv
│       │   └── payments_20261012_002.csv
│       └── 13/
│           └── payments_20261013_001.csv
```


## 5. Authentication

The ingestion utility does not use storage account keys.

Local development uses:

```text
Azure CLI Login
      |
      v
Microsoft Entra ID
      |
      v
AzureCliCredential
      |
      v
Azure Storage SDK
      |
      v
ADLS Gen2
```

This keeps credentials out of the source code.

The development identity requires appropriate Azure data-plane authorization.


## 6. Data-Plane Authorization

During implementation, Azure resource ownership alone was not sufficient to work with the underlying storage data.

The development identity therefore uses:

`Storage Blob Data Contributor`

at the storage-account scope.

This allows the ingestion process to create directories and write source deliveries while maintaining identity-based authorization.


## 7. Local Pre-Upload Validation

Before cloud delivery begins, the ingestion utility verifies that all expected local source files exist.

Example output:

```text
[FOUND] customers
[FOUND] accounts
[FOUND] cards
[FOUND] merchants
[FOUND] payments
[FOUND] transactions
[FOUND] products
[FOUND] customer_products
```

If an expected source is missing, the process stops before starting the delivery.

This reduces the chance of unintentionally creating an incomplete source batch.


## 8. Directory Creation

ADLS Gen2 uses hierarchical paths.

The uploader creates the required hierarchy before writing the file.

For example:

```text
accounts
   |
   v
accounts/2026
   |
   v
accounts/2026/10
   |
   v
accounts/2026/10/12
```

Existing directories are reused safely during subsequent executions.


## 9. Immutable Delivery Design

Landing files are treated as source-system delivery records.

An existing batch is not silently overwritten.

If this file already exists:

```text
customers/2026/10/12/customers_20261012_001.csv
```

a rerun reports:

```text
ALREADY EXISTS
```

instead of replacing it.

This provides basic idempotent behavior.


## 10. Chunked Upload

Files are uploaded using explicit ADLS file operations.

The process is:

```text
Create destination file
        |
        v
Read local chunk
        |
        v
Append chunk
        |
        v
Advance byte offset
        |
        v
Read next chunk
        |
       ...
        |
        v
Flush final file
```

The current implementation uses 4 MB chunks.

This avoids reading the entire source file into memory before transmission.

It also provides a better foundation for larger future datasets.


## 11. Upload Failure Handling

If an exception occurs while a new file is being uploaded, the ingestion utility attempts to delete the partially created destination file.

This prevents an incomplete file from remaining at the expected batch path and later being mistaken for a successfully delivered source extract.

A production implementation could extend this further with:

- Run IDs
- Delivery manifests
- Checksums
- Retry policies
- Centralized logging
- Operational alerting
- Dead-letter handling


## 12. Post-Upload Verification

After uploading a new file, the process retrieves its ADLS properties.

The cloud file size is compared against the local source size.

```text
Local source size
       |
       v
Upload
       |
       v
ADLS file properties
       |
       v
Compare byte count
       |
       +---- Match ----> Success
       |
       +---- Mismatch --> Failure
```

This provides an additional verification step beyond receiving a successful upload response.


## 13. Initial Delivery Result

The first complete landing execution processed all eight expected source datasets.

Result:

```text
Total source datasets : 8
Uploaded              : 6
Already existed       : 2
Failed                : 0

LANDING DELIVERY COMPLETED SUCCESSFULLY
```

Two files already existed because they had been created during setup and controlled troubleshooting.

They were correctly preserved rather than overwritten.


## 14. Independent ADLS Verification

The Landing Zone was independently queried after delivery.

All eight expected source files were confirmed:

```text
accounts/2026/10/12/accounts_20261012_001.csv
cards/2026/10/12/cards_20261012_001.csv
customer_products/2026/10/12/customer_products_20261012_001.csv
customers/2026/10/12/customers_20261012_001.csv
merchants/2026/10/12/merchants_20261012_001.csv
payments/2026/10/12/payments_20261012_001.csv
products/2026/10/12/products_20261012_001.csv
transactions/2026/10/12/transactions_20261012_001.csv
```

Verified cloud sizes:

| Dataset | Bytes |
|---|---:|
| accounts | 1,377,247 |
| cards | 1,110,736 |
| customer_products | 1,629,456 |
| customers | 1,653,774 |
| merchants | 602,980 |
| payments | 14,090,302 |
| products | 1,290 |
| transactions | 15,553,481 |


## 15. Engineering Issues Encountered

The implementation intentionally documents troubleshooting because operational debugging is part of data engineering.

### Issue 1 — Storage Data Access

Azure resource ownership did not initially provide access to the underlying ADLS data.

Resolution:

`Storage Blob Data Contributor`

was assigned to the development identity.

Lesson:

> Azure management-plane authorization and storage data-plane authorization are separate concerns.


### Issue 2 — Azure CLI Availability

Azure CLI was installed successfully but was not initially available through the current PowerShell PATH.

The CLI installation directory was added to the session PATH and authentication was verified.

Lesson:

> Application authentication can depend on the runtime environment, not only successful software installation.


### Issue 3 — Nested ADLS Paths

Initial troubleshooting investigated whether the nested ADLS directory structure was causing `PathNotFound`.

Independent inspection confirmed that the Python process had successfully created the required directory hierarchy.

Lesson:

> Verify each stage independently rather than assuming the visible error originated from the preceding operation.


### Issue 4 — File Upload Method

Directory creation succeeded, but the original file-upload approach continued to return `PathNotFound`.

A controlled test was performed using a small reference dataset.

The successful sequence was:

```text
create_file()
     |
     v
append_data()
     |
     v
flush_data()
```

The main ingestion utility was then updated to use this proven method.


### Issue 5 — Existing Files

Some delivery files already existed from manual setup or troubleshooting.

Instead of deleting or overwriting them, the final process detects them and reports:

```text
ALREADY EXISTS
```

Lesson:

> Rerunnable ingestion should distinguish an existing valid delivery from a failed upload.


## 16. Landing Is Not Data Cleansing

The Landing Zone deliberately preserves source-system problems.

Examples in the synthetic source data include:

- Duplicate identifiers
- Orphan foreign keys
- Invalid statuses
- Negative values
- Missing values
- Formatting inconsistencies

The uploader does not repair them.

The responsibility boundaries are:

```text
Source Generator
      |
      | creates realistic synthetic source data
      v
Landing
      |
      | preserves delivered files
      v
Bronze
      |
      | raw analytical ingestion + metadata
      v
Data Quality Framework
      |
      +------------+
      |            |
      v            v
Silver         Quarantine
```

This separation prevents transport logic from becoming mixed with business-data cleansing logic.


## 17. Current vs Future Ingestion

The current implementation is intentionally appropriate for the first FinTech360 development stage:

```text
Local synthetic extracts
        |
        v
Python batch delivery
        |
        v
ADLS Landing
```

Future platform stages will introduce more realistic patterns depending on the source domain.

Examples include:

```text
Customers / Accounts
        -> CDC / incremental ingestion

Payments / Transactions
        -> streaming / near-real-time ingestion

Products
        -> reference-data batch ingestion

Customer Products
        -> CDC / incremental ingestion
```

These capabilities will be introduced progressively rather than unnecessarily complicating the initial platform.


## 18. Next Step

The Landing Zone is now ready to act as the input boundary for the Databricks lakehouse.

The next data flow will be:

```text
ADLS Landing CSV
       |
       v
Databricks Ingestion
       |
       v
Bronze Delta
       |
       + ingestion_timestamp
       + source_file
       + batch/run metadata
       |
       v
Data Quality Processing
```

Bronze ingestion will preserve source fidelity while introducing the metadata required for traceability and downstream processing.