"""
Loan model for the Credit Approval System.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Loan(models.Model):
    """
    Represents a loan in the credit approval system.

    Tracks loan details, repayment status, and links
    to the associated customer.
    """

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='loans',
        db_index=True,
        help_text="The customer who owns this loan."
    )
    loan_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total loan principal amount.",
    )
    tenure = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Loan tenure in months."
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Annual interest rate (percentage).",
    )
    monthly_installment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Monthly EMI amount (calculated via compound interest).",
    )
    emis_paid_on_time = models.PositiveIntegerField(
        default=0,
        help_text="Number of EMIs paid on time."
    )
    start_date = models.DateField(
        help_text="Loan start date."
    )
    end_date = models.DateField(
        help_text="Loan end date."
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the loan is currently active."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['customer', 'is_active'],
                name='idx_loan_customer_active'
            ),
        ]

    def __str__(self):
        return (
            f"Loan #{self.pk} - Customer: {self.customer_id} "
            f"- Amount: {self.loan_amount}"
        )

    @property
    def repayments_left(self):
        """Calculate remaining EMI payments."""
        return max(0, self.tenure - self.emis_paid_on_time)
