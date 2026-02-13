"""
Tests for customer registration API.
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.customers.models import Customer


@override_settings(API_KEYS=['test-key'])
class RegisterCustomerTests(TestCase):
    """Test POST /api/register."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/register'
        self.header = {'HTTP_X_API_KEY': 'test-key'}
        self.valid_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': 9876543210,
        }

    def test_register_success(self):
        """Successful registration returns 201 with expected fields."""
        response = self.client.post(self.url, self.valid_data, format='json', **self.header)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('customer_id', data)
        self.assertEqual(data['name'], 'John Doe')
        self.assertEqual(data['age'], 30)
        self.assertEqual(data['monthly_income'], 50000)
        self.assertIn('approved_limit', data)
        self.assertEqual(data['phone_number'], 9876543210)

    def test_approved_limit_calculation(self):
        """approved_limit = 36 * monthly_income, rounded to nearest lakh."""
        response = self.client.post(self.url, self.valid_data, format='json', **self.header)
        data = response.json()
        # 36 * 50000 = 1800000 → nearest lakh = 1800000
        self.assertEqual(data['approved_limit'], 1800000)

    def test_approved_limit_rounding(self):
        """Test rounding to nearest lakh."""
        modified = {**self.valid_data, 'monthly_income': 45833}
        response = self.client.post(self.url, modified, format='json', **self.header)
        data = response.json()
        # 36 * 45833 = 1649988 → rounded to 1600000
        self.assertEqual(data['approved_limit'], 1600000)

    def test_customer_created_in_db(self):
        """Customer should be persisted in database."""
        self.client.post(self.url, self.valid_data, format='json', **self.header)
        self.assertEqual(Customer.objects.count(), 1)
        customer = Customer.objects.first()
        self.assertEqual(customer.first_name, 'John')
        self.assertEqual(customer.current_debt, Decimal('0.00'))

    def test_missing_first_name(self):
        """Missing required field returns 400."""
        data = {**self.valid_data}
        del data['first_name']
        response = self.client.post(self.url, data, format='json', **self.header)
        self.assertEqual(response.status_code, 400)

    def test_age_under_18(self):
        """Age under 18 should be rejected."""
        data = {**self.valid_data, 'age': 17}
        response = self.client.post(self.url, data, format='json', **self.header)
        self.assertEqual(response.status_code, 400)

    def test_invalid_phone_number(self):
        """Invalid phone number should be rejected."""
        data = {**self.valid_data, 'phone_number': 123}
        response = self.client.post(self.url, data, format='json', **self.header)
        self.assertEqual(response.status_code, 400)

    def test_zero_income_rejected(self):
        """Zero monthly income should be rejected."""
        data = {**self.valid_data, 'monthly_income': 0}
        response = self.client.post(self.url, data, format='json', **self.header)
        self.assertEqual(response.status_code, 400)
