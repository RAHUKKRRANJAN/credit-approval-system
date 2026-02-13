"""
Customer model for the Credit Approval System.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Customer(models.Model):
    """
    Represents a customer in the credit approval system.

    Stores personal information, financial details, and
    the system-calculated approved credit limit.
    """

    first_name = models.CharField(
        max_length=100,
        help_text="Customer's first name."
    )
    last_name = models.CharField(
        max_length=100,
        help_text="Customer's last name."
    )
    age = models.PositiveIntegerField(
        validators=[MinValueValidator(18)],
        help_text="Customer's age (must be 18+)."
    )
    phone_number = models.BigIntegerField(
        db_index=True,
        help_text="Customer's phone number."
    )
    monthly_salary = models.PositiveIntegerField(
        help_text="Customer's monthly income in INR."
    )
    approved_limit = models.PositiveIntegerField(
        help_text="System-approved credit limit (36 * monthly_salary, rounded to nearest lakh)."
    )
    current_debt = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Customer's current outstanding debt.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number'], name='idx_customer_phone'),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.pk})"

    @property
    def full_name(self):
        """Returns the customer's full name."""
        return f"{self.first_name} {self.last_name}"
