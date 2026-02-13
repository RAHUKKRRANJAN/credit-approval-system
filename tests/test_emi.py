"""
Tests for EMI calculation using Decimal precision.
"""

from decimal import Decimal

from django.test import TestCase

from apps.core.utils import calculate_emi, round_to_nearest_lakh


class CalculateEMITests(TestCase):
    """Test the compound interest EMI formula with Decimal."""

    def test_standard_emi(self):
        """Standard loan: 500k, 12%, 24 months."""
        emi = calculate_emi(Decimal('500000'), Decimal('12'), 24)
        self.assertIsInstance(emi, Decimal)
        self.assertAlmostEqual(float(emi), 23536.74, places=0)

    def test_high_rate(self):
        """High interest rate: 24%."""
        emi = calculate_emi(Decimal('100000'), Decimal('24'), 12)
        self.assertIsInstance(emi, Decimal)
        self.assertGreater(emi, Decimal('9000'))

    def test_zero_interest(self):
        """0% interest → simple division."""
        emi = calculate_emi(Decimal('120000'), Decimal('0'), 12)
        self.assertEqual(emi, Decimal('10000.00'))

    def test_one_month_tenure(self):
        """1 month tenure."""
        emi = calculate_emi(Decimal('100000'), Decimal('12'), 1)
        self.assertEqual(emi, Decimal('101000.00'))

    def test_small_loan(self):
        """Very small loan."""
        emi = calculate_emi(Decimal('1000'), Decimal('10'), 6)
        self.assertIsInstance(emi, Decimal)
        self.assertGreater(emi, Decimal('0'))

    def test_large_loan(self):
        """Large loan: 50 crore, 10%, 360 months."""
        emi = calculate_emi(Decimal('500000000'), Decimal('10'), 360)
        self.assertIsInstance(emi, Decimal)
        self.assertGreater(emi, Decimal('4000000'))

    def test_low_interest(self):
        """Very low interest rate: 0.5%."""
        emi = calculate_emi(Decimal('100000'), Decimal('0.5'), 12)
        self.assertIsInstance(emi, Decimal)
        self.assertGreater(emi, Decimal('8000'))

    def test_invalid_principal(self):
        """Negative principal raises ValueError."""
        with self.assertRaises(ValueError):
            calculate_emi(Decimal('-1'), Decimal('10'), 12)

    def test_zero_principal(self):
        with self.assertRaises(ValueError):
            calculate_emi(Decimal('0'), Decimal('10'), 12)

    def test_negative_rate(self):
        with self.assertRaises(ValueError):
            calculate_emi(Decimal('100000'), Decimal('-1'), 12)

    def test_zero_tenure(self):
        with self.assertRaises(ValueError):
            calculate_emi(Decimal('100000'), Decimal('10'), 0)

    def test_returns_two_decimal_places(self):
        """EMI should always be quantized to 2 decimal places."""
        emi = calculate_emi(Decimal('333333'), Decimal('7.77'), 17)
        self.assertEqual(emi, emi.quantize(Decimal('0.01')))

    def test_manual_verification_15_percent(self):
        """Manually verified: P=500000, r=15%/12=0.0125, n=24."""
        emi = calculate_emi(Decimal('500000'), Decimal('15'), 24)
        # Exact calculation: 24243.32
        self.assertEqual(emi, Decimal('24243.32'))

    def test_accepts_int_and_float_inputs(self):
        """calculate_emi should coerce int/float to Decimal."""
        emi1 = calculate_emi(100000, 12, 12)
        emi2 = calculate_emi(100000.0, 12.0, 12)
        emi3 = calculate_emi(Decimal('100000'), Decimal('12'), 12)
        self.assertEqual(emi1, emi3)
        self.assertEqual(emi2, emi3)


class RoundToNearestLakhTests(TestCase):
    """Tests for the rounding utility."""

    def test_round_down(self):
        self.assertEqual(round_to_nearest_lakh(1620000), 1600000)

    def test_round_up(self):
        self.assertEqual(round_to_nearest_lakh(1680000), 1700000)

    def test_exact_half_rounds_up(self):
        self.assertEqual(round_to_nearest_lakh(1650000), 1700000)

    def test_exact_lakh(self):
        self.assertEqual(round_to_nearest_lakh(1800000), 1800000)

    def test_zero(self):
        self.assertEqual(round_to_nearest_lakh(0), 0)

    def test_negative(self):
        self.assertEqual(round_to_nearest_lakh(-500000), 0)

    def test_small_amount(self):
        self.assertEqual(round_to_nearest_lakh(50000), 100000)

    def test_very_large(self):
        self.assertEqual(round_to_nearest_lakh(99950000), 100000000)
