"""
Tests for eligibility check API, including slab logic,
interest rate correction, and loan amount vs approved limit.
"""

from decimal import Decimal
from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.loans.models import Loan


@override_settings(API_KEYS=['test-key'])
class CheckEligibilityTests(TestCase):
    """Test POST /api/check-eligibility."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/check-eligibility'
        self.header = {'HTTP_X_API_KEY': 'test-key'}
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='User',
            age=30,
            phone_number=9876543210,
            monthly_salary=50000,
            approved_limit=1800000,
        )

    def test_eligible_high_score(self):
        """Customer with score > 50 → approved at any rate."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '8.00',
            'tenure': 12,
        }, format='json', **self.header)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['approval'])

    def test_response_has_all_fields(self):
        """Response must contain all required fields."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        data = response.json()
        required_fields = [
            'customer_id', 'approval', 'interest_rate',
            'corrected_interest_rate', 'tenure', 'monthly_installment',
        ]
        for field in required_fields:
            self.assertIn(field, data)

    def test_interest_rate_correction_slab2(self):
        """Score 30-50: rate corrected to 12% if lower."""
        # Force score 30-50 by giving no loan history (score=50)
        # Score 50 is in slab 2 (30 < 50 <= 50)
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '8.00',
            'tenure': 12,
        }, format='json', **self.header)
        data = response.json()

        # Baseline score is 50 → slab 2 → rate corrected to 12.0
        # Compare as float to handle both string ("12.00") and float (12.0) serialization
        self.assertEqual(float(data['corrected_interest_rate']), 12.0)

    def test_emi_exceeds_50_percent_salary_rejected(self):
        """If current EMIs >= 50% salary → reject."""
        # Create a large existing loan eating up salary
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('1000000'),
            tenure=60,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('30000.00'),  # > 50% of 50000
            emis_paid_on_time=5,
            start_date=date(2023, 1, 1),
            end_date=date(2028, 1, 1),
            is_active=True,
        )
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '50000.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        data = response.json()
        self.assertFalse(data['approval'])

    def test_customer_not_found(self):
        """Non-existent customer → 404."""
        response = self.client.post(self.url, {
            'customer_id': 9999,
            'loan_amount': '100000.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        self.assertEqual(response.status_code, 404)

    def test_negative_loan_amount(self):
        """Negative loan amount → 400."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '-1.00',
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        self.assertEqual(response.status_code, 400)

    def test_loan_amount_exceeds_approved_limit(self):
        """Loan amount > approved_limit → rejected."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '5000000.00',  # > 1800000
            'interest_rate': '10.00',
            'tenure': 12,
        }, format='json', **self.header)
        data = response.json()
        self.assertFalse(data['approval'])

    def test_monthly_installment_is_decimal_string(self):
        """monthly_installment should be a proper decimal or float."""
        response = self.client.post(self.url, {
            'customer_id': self.customer.pk,
            'loan_amount': '100000.00',
            'interest_rate': '12.00',
            'tenure': 12,
        }, format='json', **self.header)
        data = response.json()
        # Should be positive number (float or string)
        val = data['monthly_installment']
        self.assertTrue(isinstance(val, (str, float, Decimal)))
        self.assertGreater(float(val), 0)
