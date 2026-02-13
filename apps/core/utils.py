"""
Core utility functions for the Credit Approval System.

Contains financial calculation helpers used across the application.
All financial calculations use Python's Decimal for precision.
"""

import math
from decimal import ROUND_HALF_UP, Decimal, getcontext

# Set high precision for intermediate financial calculations
getcontext().prec = 28


def calculate_emi(
    principal: Decimal,
    annual_rate: Decimal,
    tenure_months: int,
) -> Decimal:
    """
    Calculate EMI using compound interest formula with Decimal precision.

    EMI = P × r × (1+r)^n / ((1+r)^n - 1)

    Where:
        P = principal (loan amount)
        r = monthly interest rate (annual_rate / 12 / 100)
        n = tenure in months

    Args:
        principal: Loan amount (must be > 0). Accepts Decimal, float, or int.
        annual_rate: Annual interest rate as percentage (e.g., 12 for 12%).
        tenure_months: Number of months for repayment (must be >= 1).

    Returns:
        Monthly EMI amount as Decimal, quantized to 2 decimal places (ROUND_HALF_UP).

    Raises:
        ValueError: If inputs are invalid.
    """
    # Coerce to Decimal for safety
    principal = Decimal(str(principal))
    annual_rate = Decimal(str(annual_rate))

    if principal <= 0:
        raise ValueError("Principal must be greater than 0.")
    if annual_rate < 0:
        raise ValueError("Interest rate cannot be negative.")
    if tenure_months < 1:
        raise ValueError("Tenure must be at least 1 month.")

    TWO_PLACES = Decimal('0.01')

    # Handle 0% interest rate edge case
    if annual_rate == 0:
        emi = principal / Decimal(str(tenure_months))
        return emi.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # Monthly interest rate
    monthly_rate = annual_rate / Decimal('1200')

    # Compound interest EMI formula using Decimal exponentiation
    one_plus_r = Decimal('1') + monthly_rate
    power_term = one_plus_r ** tenure_months
    emi = principal * monthly_rate * power_term / (power_term - Decimal('1'))

    return emi.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def round_to_nearest_lakh(amount: float) -> int:
    """
    Round an amount to the nearest lakh (100,000).

    Uses traditional rounding (half rounds up).

    Args:
        amount: The amount to round.

    Returns:
        Amount rounded to the nearest lakh as an integer.

    Examples:
        round_to_nearest_lakh(1620000) → 1600000
        round_to_nearest_lakh(1650000) → 1700000
        round_to_nearest_lakh(1800000) → 1800000
    """
    if amount <= 0:
        return 0
    lakh = 100000
    return int(math.floor(amount / lakh + 0.5)) * lakh
