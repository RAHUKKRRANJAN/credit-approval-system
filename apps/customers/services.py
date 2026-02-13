"""
Customer service layer.

All customer-related business logic resides here.
Views delegate to this service — no business logic in views.
"""

import logging

from apps.core.utils import round_to_nearest_lakh
from apps.customers.models import Customer

logger = logging.getLogger(__name__)


class CustomerService:
    """Service class for customer-related operations."""

    @staticmethod
    def register(validated_data: dict) -> Customer:
        """
        Register a new customer.

        Calculates approved_limit as 36 * monthly_salary,
        rounded to the nearest lakh.

        Args:
            validated_data: Dict with first_name, last_name, age,
                          monthly_income, phone_number.

        Returns:
            The newly created Customer instance.
        """
        monthly_income = validated_data['monthly_income']
        raw_limit = 36 * monthly_income
        approved_limit = round_to_nearest_lakh(raw_limit)

        customer = Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            age=validated_data['age'],
            phone_number=validated_data['phone_number'],
            monthly_salary=monthly_income,
            approved_limit=approved_limit,
        )

        logger.info(
            "Registered customer %s (ID: %d) with approved_limit=%d",
            customer.full_name,
            customer.pk,
            approved_limit,
        )

        return customer

    @staticmethod
    def get_customer(customer_id: int) -> Customer:
        """
        Retrieve a customer by ID.

        Args:
            customer_id: The customer's primary key.

        Returns:
            Customer instance.

        Raises:
            Customer.DoesNotExist: If customer not found.
        """
        return Customer.objects.get(pk=customer_id)
