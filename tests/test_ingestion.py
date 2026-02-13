"""
Tests for the data ingestion Celery tasks.

Uses task.apply() with CELERY_ALWAYS_EAGER to run tasks synchronously
in the test environment.
"""

import os
import tempfile

import pandas as pd
from django.test import TestCase, override_settings

from apps.core.tasks import ingest_customer_data, ingest_loan_data
from apps.customers.models import Customer
from apps.loans.models import Loan


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class CustomerIngestionTests(TestCase):
    """Test cases for customer data ingestion."""

    def setUp(self):
        """Create a temporary Excel file for testing."""
        self.temp_dir = tempfile.mkdtemp()

        # Create test customer data
        data = {
            'customer_id': [1, 2, 3],
            'first_name': ['Alice', 'Bob', 'Charlie'],
            'last_name': ['Smith', 'Jones', 'Brown'],
            'age': [25, 35, 45],
            'phone_number': [9876543210, 9876543211, 9876543212],
            'monthly_salary': [50000, 75000, 100000],
            'approved_limit': [1800000, 2700000, 3600000],
            'current_debt': [0, 50000, 100000],
        }
        df = pd.DataFrame(data)
        df.to_excel(
            os.path.join(self.temp_dir, 'customer_data.xlsx'),
            index=False,
        )

    @override_settings()
    def test_ingest_customer_data(self):
        """Test successful customer data ingestion."""
        from django.conf import settings
        settings.DATA_DIR = self.temp_dir

        result = ingest_customer_data.apply().get()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_rows'], 3)
        self.assertEqual(result['created'], 3)
        self.assertEqual(result['errors'], 0)

        # Verify data in DB
        self.assertEqual(Customer.objects.count(), 3)
        alice = Customer.objects.get(pk=1)
        self.assertEqual(alice.first_name, 'Alice')
        self.assertEqual(alice.monthly_salary, 50000)

    @override_settings()
    def test_ingest_idempotent(self):
        """Test that running ingestion twice doesn't create duplicates."""
        from django.conf import settings
        settings.DATA_DIR = self.temp_dir

        ingest_customer_data.apply().get()
        result = ingest_customer_data.apply().get()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(Customer.objects.count(), 3)
        self.assertEqual(result['updated'], 3)

    @override_settings()
    def test_missing_file(self):
        """Test graceful handling of missing file."""
        from django.conf import settings
        settings.DATA_DIR = '/nonexistent/path'

        result = ingest_customer_data.apply().get()
        self.assertEqual(result['status'], 'error')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class LoanIngestionTests(TestCase):
    """Test cases for loan data ingestion."""

    def setUp(self):
        """Create test data."""
        self.temp_dir = tempfile.mkdtemp()

        # Create customers first
        Customer.objects.create(
            pk=1,
            first_name='Alice',
            last_name='Smith',
            age=25,
            phone_number=9876543210,
            monthly_salary=50000,
            approved_limit=1800000,
        )

        # Create test loan data
        data = {
            'customer_id': [1, 1],
            'loan_id': [101, 102],
            'loan_amount': [100000, 200000],
            'tenure': [12, 24],
            'interest_rate': [10.0, 12.0],
            'monthly_repayment': [8792, 9414],
            'emis_paid_on_time': [10, 20],
            'start_date': ['2023-01-01', '2023-06-01'],
            'end_date': ['2024-01-01', '2025-06-01'],
        }
        df = pd.DataFrame(data)
        df.to_excel(
            os.path.join(self.temp_dir, 'loan_data.xlsx'),
            index=False,
        )

    @override_settings()
    def test_ingest_loan_data(self):
        """Test successful loan data ingestion."""
        from django.conf import settings
        settings.DATA_DIR = self.temp_dir

        result = ingest_loan_data.apply().get()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_rows'], 2)
        self.assertEqual(result['created'], 2)
        self.assertEqual(result['errors'], 0)

        # Verify data in DB
        self.assertEqual(Loan.objects.count(), 2)

    @override_settings()
    def test_loan_ingestion_idempotent(self):
        """Test that running ingestion twice doesn't create duplicates."""
        from django.conf import settings
        settings.DATA_DIR = self.temp_dir

        ingest_loan_data.apply().get()
        result = ingest_loan_data.apply().get()

        self.assertEqual(Loan.objects.count(), 2)
        self.assertEqual(result['updated'], 2)

    @override_settings()
    def test_invalid_customer_skipped(self):
        """Test that loans with invalid customer IDs are skipped."""
        from django.conf import settings

        # Create loan data with invalid customer_id
        data = {
            'customer_id': [999],  # Non-existent
            'loan_id': [201],
            'loan_amount': [100000],
            'tenure': [12],
            'interest_rate': [10.0],
            'monthly_repayment': [8792],
            'emis_paid_on_time': [10],
            'start_date': ['2023-01-01'],
            'end_date': ['2024-01-01'],
        }
        df = pd.DataFrame(data)
        temp_dir2 = tempfile.mkdtemp()
        df.to_excel(
            os.path.join(temp_dir2, 'loan_data.xlsx'),
            index=False,
        )

        settings.DATA_DIR = temp_dir2
        result = ingest_loan_data.apply().get()

        self.assertEqual(result['errors'], 1)
        self.assertEqual(Loan.objects.count(), 0)
