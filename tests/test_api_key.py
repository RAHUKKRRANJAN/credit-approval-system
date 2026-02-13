"""
Tests for API key authentication middleware.
"""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(API_KEYS=['test-api-key-123', 'another-key-456'])
class APIKeyAuthTests(TestCase):
    """Test X-API-KEY header authentication."""

    def setUp(self):
        self.client = APIClient()

    def test_missing_api_key_returns_401(self):
        """Request without X-API-KEY → 401."""
        response = self.client.post('/api/register', {
            'first_name': 'Test',
            'last_name': 'User',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': 9876543210,
        }, format='json')
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertTrue(data['error'])
        self.assertIn('Authentication required', data['detail'])

    def test_invalid_api_key_returns_403(self):
        """Request with wrong X-API-KEY → 403."""
        response = self.client.post(
            '/api/register',
            {
                'first_name': 'Test',
                'last_name': 'User',
                'age': 30,
                'monthly_income': 50000,
                'phone_number': 9876543210,
            },
            format='json',
            HTTP_X_API_KEY='wrong-key',
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('Invalid API key', data['detail'])

    def test_valid_api_key_passes(self):
        """Request with valid X-API-KEY → proceeds normally."""
        response = self.client.post(
            '/api/register',
            {
                'first_name': 'Test',
                'last_name': 'User',
                'age': 30,
                'monthly_income': 50000,
                'phone_number': 9876543210,
            },
            format='json',
            HTTP_X_API_KEY='test-api-key-123',
        )
        self.assertEqual(response.status_code, 201)

    def test_second_valid_key_works(self):
        """Multiple API keys are supported."""
        response = self.client.post(
            '/api/register',
            {
                'first_name': 'Test',
                'last_name': 'User2',
                'age': 25,
                'monthly_income': 60000,
                'phone_number': 9876543211,
            },
            format='json',
            HTTP_X_API_KEY='another-key-456',
        )
        self.assertEqual(response.status_code, 201)

    def test_health_endpoint_exempt(self):
        """GET /health/ should work without API key."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')

    def test_all_api_endpoints_require_key(self):
        """All /api/ endpoints should require API key."""
        endpoints = [
            ('post', '/api/register'),
            ('post', '/api/check-eligibility'),
            ('post', '/api/create-loan'),
            ('get', '/api/view-loan/1'),
            ('get', '/api/view-loans/1'),
        ]
        for method, url in endpoints:
            response = getattr(self.client, method)(url, format='json')
            self.assertEqual(
                response.status_code, 401,
                f"{method.upper()} {url} should require API key",
            )


@override_settings(API_KEYS=[])
class APIKeyDisabledTests(TestCase):
    """When API_KEYS is empty, middleware should be disabled."""

    def setUp(self):
        self.client = APIClient()

    def test_empty_api_keys_allows_requests(self):
        """With no API_KEYS configured, all requests pass through."""
        response = self.client.post('/api/register', {
            'first_name': 'Test',
            'last_name': 'NoAuth',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': 9876543210,
        }, format='json')
        self.assertEqual(response.status_code, 201)
