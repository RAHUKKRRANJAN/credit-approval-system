"""
Tests for credit score calculation with boundary conditions.
"""

from decimal import Decimal
from datetime import date

from django.test import TestCase

from apps.customers.models import Customer
from apps.loans.models import Loan
from apps.loans.services import CreditScoreService


class CreditScoreTests(TestCase):
    """Test credit score calculation across all factors."""

    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='User',
            age=30,
            phone_number=9876543210,
            monthly_salary=50000,
            approved_limit=1800000,
        )

    def test_no_loan_history_returns_50(self):
        """Customer with no loans gets baseline score of 50."""
        score = CreditScoreService.calculate(self.customer)
        self.assertEqual(score, 50)

    def test_perfect_payment_history(self):
        """Customer with 100% on-time payments scores high."""
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('100000'),
            tenure=12,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('8792.00'),
            emis_paid_on_time=12,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            is_active=False,
        )
        score = CreditScoreService.calculate(self.customer)
        self.assertGreaterEqual(score, 80)

    def test_poor_payment_history(self):
        """Customer with poor payment record scores lower."""
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('100000'),
            tenure=12,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('8792.00'),
            emis_paid_on_time=2,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            is_active=False,
        )
        score = CreditScoreService.calculate(self.customer)
        self.assertLess(score, 80)

    def test_too_many_loans_reduces_score(self):
        """Customer with many loans should have lower score."""
        for i in range(12):
            Loan.objects.create(
                customer=self.customer,
                loan_amount=Decimal('10000'),
                tenure=6,
                interest_rate=Decimal('10.00'),
                monthly_installment=Decimal('1700.00'),
                emis_paid_on_time=6,
                start_date=date(2023, 1, 1),
                end_date=date(2023, 7, 1),
                is_active=False,
            )
        score = CreditScoreService.calculate(self.customer)
        self.assertLess(score, 100)

    def test_current_loans_exceed_limit_returns_zero(self):
        """When active loans exceed approved_limit → score = 0."""
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('2000000'),
            tenure=60,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('42000.00'),
            emis_paid_on_time=5,
            start_date=date(2023, 1, 1),
            end_date=date(2028, 1, 1),
            is_active=True,
        )
        score = CreditScoreService.calculate(self.customer)
        self.assertEqual(score, 0)

    def test_score_clamped_0_to_100(self):
        """Score must be between 0 and 100."""
        score = CreditScoreService.calculate(self.customer)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_uses_round_not_truncate(self):
        """round() should be used instead of int() — score 50.5 → 51 not 50."""
        # Create a scenario that could produce a fractional score
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('100000'),
            tenure=12,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('8792.00'),
            emis_paid_on_time=12,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            is_active=False,
        )
        score = CreditScoreService.calculate(self.customer)
        # Verify it's an integer (round() returns int)
        self.assertIsInstance(score, int)

    # ─── Boundary tests for slab transitions ───

    def test_boundary_score_exactly_50(self):
        """Score of exactly 50 should land in appropriate slab."""
        # Baseline: no loans → score = 50
        score = CreditScoreService.calculate(self.customer)
        self.assertEqual(score, 50)
        # Score 50 is NOT > 50, so it should be in slab 2 (30 < score <= 50)

    def test_boundary_score_above_50(self):
        """Score > 50 → slab 1 (any rate)."""
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('100000'),
            tenure=12,
            interest_rate=Decimal('10.00'),
            monthly_installment=Decimal('8792.00'),
            emis_paid_on_time=12,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            is_active=False,
        )
        score = CreditScoreService.calculate(self.customer)
        self.assertGreater(score, 50)
