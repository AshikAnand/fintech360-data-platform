# FinTech360 Source Data Model

## 1. Overview

FinTech360 is a fictional digital financial-services platform designed to simulate a modern FinTech data ecosystem.

The platform supports customer accounts, debit and credit cards, merchant payments, financial transactions, and multiple financial products.

This source data model forms the operational foundation for the FinTech360 Data Platform.

The source systems will eventually feed an Azure Databricks lakehouse architecture using:

- Bronze layer for raw ingestion
- Silver layer for validated and conformed data
- Gold layer for business-ready data products

## 2. Core Source Entities

The initial FinTech360 source model contains the following entities:

1. Customers
2. Accounts
3. Cards
4. Merchants
5. Payments
6. Transactions
7. Products
8. Customer Products