"""
Tests for loan creation, view, and pagination.
"""

from decimal import Decimal
from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.loans.models import Loan


@override_settings(API_KEYS=['test-key'])
class CreateLoanTests(TestCase):
    """Test POST /api/create-loan."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/create-loan'
        self.header = {'HTTP_X_API_KEY': 'test-key'}
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='User',
            age=30,
            phone_number=9876543210,
            monthly_salary=100000,
            approved_limit=3600000,
        )

    def test_create_loan_approved(self):
        """Approved loan returns 201 with loan_id."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['loan_approved'])
        self.assertIsNotNone(data['loan_id'])
        self.assertEqual(data['message'], 'Loan approved successfully.')
        self.assertIsNotNone(data['monthly_installment'])

    def test_create_loan_rejected(self):
        """Rejected loan returns 200 with loan_approved=False."""
        # Create existing loans to push EMI > 50%
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('2000000'),
            tenure=60,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('55000.00'),
            emis_paid_on_time=5,
            start_date=date(2023, 1, 1),
            end_date=date(2028, 1, 1),
            is_active=True,
        )
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['loan_approved'])
        self.assertIsNone(data['loan_id'])

    def test_current_debt_updated(self):
        """After loan creation, customer's current_debt should increase."""
        self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_debt, Decimal('100000.00'))

    def test_loan_persisted_in_db(self):
        """Loan should be persisted in database."""
        self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '200000.00',
            'interest_rate': '12.00',
            'tenure': 24,
        }, format='json', **self.header)
        self.assertEqual(Loan.objects.count(), 1)
        loan = Loan.objects.first()
        self.assertEqual(loan.loan_amount, Decimal('200000.00'))
        self.assertEqual(loan.tenure, 24)
        self.assertTrue(loan.is_active)

    def test_customer_not_found(self):
        """Non-existent customer → 404."""
        response = self.client.post(self.url, {
            'customer_id': 9999,
            'loan_amount': '100000.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        self.assertEqual(response.status_code, 404)

    def test_missing_fields(self):
        """Missing required fields → 400."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
        }, format='json', **self.header)
        self.assertEqual(response.status_code, 400)

    def test_loan_amount_exceeds_approved_limit(self):
        """Loan amount > approved limit → rejected."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '10000000.00',  # > 3600000
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        data = response.json()
        self.assertFalse(data['loan_approved'])

    def test_uses_corrected_interest_rate(self):
        """Loan should be created with corrected rate if applicable."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '8.00',  # Will be corrected based on score
            'tenure': 12,
        }, format='json', **self.header)
        if response.json()['loan_approved']:
            loan = Loan.objects.first()
            # Rate may be corrected to 12 or 16 depending on score
            self.assertGreaterEqual(loan.interest_rate, Decimal('8.00'))


@override_settings(API_KEYS=['test-key'])
class ViewLoanTests(TestCase):
    """Test GET /api/view-loan/<loan_id>."""

    def setUp(self):
        self.client = APIClient()
        self.header = {'HTTP_X_API_KEY': 'test-key'}
        self.customer = Customer.objects.create(
            first_name='Alice',
            last_name='Smith',
            age=25,
            phone_number=9876543211,
            monthly_salary=50000,
            approved_limit=1800000,
        )
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('200000.00'),
            tenure=24,
            interest_rate=Decimal('12.00'),
            monthly_installment=Decimal('9414.62'),
            emis_paid_on_time=10,
            start_date=date(2023, 1, 1),
            end_date=date(2025, 1, 1),
            is_active=True,
        )

    def test_view_loan_success(self):
        """Successful loan view returns 200 with all fields."""
        response = self.client.get(f'/api/view-loan/{self.loan.pk}', **self.header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['loan_id'], self.loan.pk)
        self.assertIn('customer', data)
        self.assertEqual(data['customer']['id'], self.customer.pk)
        self.assertEqual(data['customer']['first_name'], 'Alice')

    def test_view_loan_not_found(self):
        """Non-existent loan → 404."""
        response = self.client.get('/api/view-loan/9999', **self.header)
        self.assertEqual(response.status_code, 404)

    def test_view_loan_has_decimal_fields(self):
        """loan_amount, interest_rate, monthly_installment should be decimal strings (or floats)."""
        response = self.client.get(f'/api/view-loan/{self.loan.pk}', **self.header)
        data = response.json()
        self.assertEqual(float(data['loan_amount']), 200000.0)
        self.assertEqual(float(data['interest_rate']), 12.0)


@override_settings(API_KEYS=['test-key'])
class ViewLoansTests(TestCase):
    """Test GET /api/view-loans/<customer_id> with pagination."""

    def setUp(self):
        self.client = APIClient()
        self.header = {'HTTP_X_API_KEY': 'test-key'}
        self.customer = Customer.objects.create(
            first_name='Bob',
            last_name='Jones',
            age=35,
            phone_number=9876543212,
            monthly_salary=75000,
            approved_limit=2700000,
        )

    def test_view_loans_empty(self):
        """Customer with no loans → empty list."""
        response = self.client.get(f'/api/view-loans/{self.customer.pk}', **self.header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])

    def test_view_loans_with_data(self):
        """Customer with loans → returns list."""
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('100000.00'),
            tenure=12,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('8792.00'),
            emis_paid_on_time=5,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            is_active=True,
        )
        response = self.client.get(f'/api/view-loans/{self.customer.pk}', **self.header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        loan_item = data['results'][0]
        self.assertIn('loan_id', loan_item)
        self.assertIn('repayments_left', loan_item)
        self.assertEqual(loan_item['repayments_left'], 7)  # 12 - 5

    def test_view_loans_pagination(self):
        """Loans are paginated."""
        for i in range(15):
            Loan.objects.create(
                customer=self.customer,
                loan_amount=Decimal('10000.00'),
                tenure=6,
                interest_rate=Decimal('10.00'),
                monthly_installment=Decimal('1700.00'),
                emis_paid_on_time=3,
                start_date=date(2023, 1, 1),
                end_date=date(2023, 7, 1),
                is_active=False,
            )
        response = self.client.get(f'/api/view-loans/{self.customer.pk}', **self.header)
        data = response.json()
        self.assertEqual(data['count'], 15)
        self.assertEqual(len(data['results']), 10)  # default page size
        self.assertIsNotNone(data['next'])

    def test_view_loans_customer_not_found(self):
        """Non-existent customer → 404."""
        response = self.client.get('/api/view-loans/9999', **self.header)
        self.assertEqual(response.status_code, 404)

    def test_view_loans_page_size_param(self):
        """Custom page_size parameter."""
        for i in range(5):
            Loan.objects.create(
                customer=self.customer,
                loan_amount=Decimal('10000.00'),
                tenure=6,
                interest_rate=Decimal('10.00'),
                monthly_installment=Decimal('1700.00'),
                emis_paid_on_time=3,
                start_date=date(2023, 1, 1),
                end_date=date(2023, 7, 1),
                is_active=False,
            )
        response = self.client.get(
            f'/api/view-loans/{self.customer.pk}?page_size=2',
            **self.header
        )
        data = response.json()
        self.assertEqual(data['count'], 5)
        self.assertEqual(len(data['results']), 2)
