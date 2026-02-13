"""
Celery tasks for data ingestion.

Reads customer_data.xlsx and loan_data.xlsx using pandas
and bulk inserts into PostgreSQL with idempotency guarantees.
"""

import logging
from decimal import Decimal
from pathlib import Path

import pandas as pd
from celery import shared_task
from django.conf import settings
from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='core.ingest_customer_data',
    max_retries=3,
    default_retry_delay=10,
)
def ingest_customer_data(self):
    """
    Ingest customer data from customer_data.xlsx.

    Reads the Excel file, validates data, and performs
    bulk insert with duplicate handling via update_or_create.

    This task is idempotent — safe to run multiple times.
    """
    from apps.customers.models import Customer

    file_path = Path(settings.DATA_DIR) / 'customer_data.xlsx'

    if not file_path.exists():
        logger.error("Customer data file not found: %s", file_path)
        return {'status': 'error', 'message': f'File not found: {file_path}'}

    try:
        logger.info("Starting customer data ingestion from %s", file_path)

        df = pd.read_excel(file_path)
        logger.info("Read %d rows from customer_data.xlsx", len(df))

        # Normalize column names
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

        created_count = 0
        updated_count = 0
        error_count = 0

        for index, row in df.iterrows():
            try:
                customer_data = {
                    'first_name': str(row.get('first_name', '')).strip(),
                    'last_name': str(row.get('last_name', '')).strip(),
                    'age': int(row.get('age', 0)),
                    'phone_number': int(row.get('phone_number', 0)),
                    'monthly_salary': int(row.get('monthly_salary', 0)),
                    'approved_limit': int(row.get('approved_limit', 0)),
                }

                # Handle current_debt — may be named differently
                current_debt = row.get('current_debt', 0)
                if pd.isna(current_debt):
                    current_debt = 0
                customer_data['current_debt'] = Decimal(str(current_debt))

                customer_id = row.get('customer_id')
                if pd.isna(customer_id):
                    logger.warning(
                        "Row %d: missing customer_id, skipping", index
                    )
                    error_count += 1
                    continue

                _, created = Customer.objects.update_or_create(
                    pk=int(customer_id),
                    defaults=customer_data,
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except (ValueError, TypeError, IntegrityError) as e:
                logger.warning(
                    "Row %d: failed to process — %s", index, str(e)
                )
                error_count += 1
                continue

        result = {
            'status': 'success',
            'total_rows': len(df),
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
        }
        logger.info("Customer data ingestion complete: %s", result)
        return result

    except Exception as exc:
        logger.exception("Customer data ingestion failed")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name='core.ingest_loan_data',
    max_retries=3,
    default_retry_delay=10,
)
def ingest_loan_data(self):
    """
    Ingest loan data from loan_data.xlsx.

    Reads the Excel file, validates data, and performs
    bulk insert with duplicate handling via update_or_create.

    This task is idempotent — safe to run multiple times.
    """
    from apps.customers.models import Customer
    from apps.loans.models import Loan

    file_path = Path(settings.DATA_DIR) / 'loan_data.xlsx'

    if not file_path.exists():
        logger.error("Loan data file not found: %s", file_path)
        return {'status': 'error', 'message': f'File not found: {file_path}'}

    try:
        logger.info("Starting loan data ingestion from %s", file_path)

        df = pd.read_excel(file_path)
        logger.info("Read %d rows from loan_data.xlsx", len(df))

        # Normalize column names
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

        # Get valid customer IDs for validation
        valid_customer_ids = set(
            Customer.objects.values_list('pk', flat=True)
        )

        created_count = 0
        updated_count = 0
        error_count = 0

        for index, row in df.iterrows():
            try:
                customer_id = row.get('customer_id')
                loan_id = row.get('loan_id')

                if pd.isna(customer_id) or pd.isna(loan_id):
                    logger.warning(
                        "Row %d: missing customer_id or loan_id, skipping",
                        index,
                    )
                    error_count += 1
                    continue

                customer_id = int(customer_id)
                loan_id = int(loan_id)

                if customer_id not in valid_customer_ids:
                    logger.warning(
                        "Row %d: customer_id %d not found, skipping",
                        index,
                        customer_id,
                    )
                    error_count += 1
                    continue

                # Parse dates
                start_date = pd.to_datetime(
                    row.get('start_date'), errors='coerce'
                )
                end_date = pd.to_datetime(
                    row.get('end_date'), errors='coerce'
                )

                if pd.isna(start_date) or pd.isna(end_date):
                    logger.warning(
                        "Row %d: invalid dates, skipping", index
                    )
                    error_count += 1
                    continue

                # Determine if loan is active
                from datetime import date as dt_date
                is_active = end_date.date() >= dt_date.today()

                # Handle EMI column name variations
                monthly_repayment = row.get(
                    'monthly_repayment',
                    row.get('monthly_payment', row.get('emi', 0)),
                )
                if pd.isna(monthly_repayment):
                    monthly_repayment = 0

                emis_paid = row.get('emis_paid_on_time', 0)
                if pd.isna(emis_paid):
                    emis_paid = 0

                loan_amount = row.get('loan_amount', 0)
                if pd.isna(loan_amount):
                    loan_amount = 0

                interest_rate = row.get('interest_rate', 0)
                if pd.isna(interest_rate):
                    interest_rate = 0

                tenure = row.get('tenure', 0)
                if pd.isna(tenure):
                    tenure = 0

                loan_data = {
                    'customer_id': customer_id,
                    'loan_amount': Decimal(str(loan_amount)),
                    'tenure': int(tenure),
                    'interest_rate': Decimal(str(interest_rate)),
                    'monthly_installment': Decimal(str(monthly_repayment)),
                    'emis_paid_on_time': int(emis_paid),
                    'start_date': start_date.date(),
                    'end_date': end_date.date(),
                    'is_active': is_active,
                }

                _, created = Loan.objects.update_or_create(
                    pk=loan_id,
                    defaults=loan_data,
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except (ValueError, TypeError, IntegrityError) as e:
                logger.warning(
                    "Row %d: failed to process — %s", index, str(e)
                )
                error_count += 1
                continue

        result = {
            'status': 'success',
            'total_rows': len(df),
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
        }
        logger.info("Loan data ingestion complete: %s", result)
        return result

    except Exception as exc:
        logger.exception("Loan data ingestion failed")
        raise self.retry(exc=exc)
