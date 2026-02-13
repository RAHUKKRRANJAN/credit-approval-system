"""
Customer serializers for the Credit Approval System.
"""

from rest_framework import serializers


class RegisterCustomerSerializer(serializers.Serializer):
    """Serializer for customer registration request."""

    first_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Customer's first name.",
    )
    last_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Customer's last name.",
    )
    age = serializers.IntegerField(
        min_value=18,
        max_value=120,
        required=True,
        help_text="Customer's age (must be 18+).",
    )
    monthly_income = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="Customer's monthly income in INR.",
    )
    phone_number = serializers.IntegerField(
        required=True,
        help_text="Customer's phone number.",
    )

    def validate_phone_number(self, value):
        """Validate phone number is a valid 10-digit number."""
        if value < 1000000000 or value > 9999999999:
            raise serializers.ValidationError(
                "Phone number must be a valid 10-digit number."
            )
        return value


class CustomerResponseSerializer(serializers.Serializer):
    """Serializer for customer registration response."""

    customer_id = serializers.IntegerField()
    name = serializers.CharField()
    age = serializers.IntegerField()
    monthly_income = serializers.IntegerField()
    approved_limit = serializers.IntegerField()
    phone_number = serializers.IntegerField()


class CustomerDetailSerializer(serializers.Serializer):
    """Serializer for embedded customer details in loan response."""

    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.IntegerField()
    age = serializers.IntegerField()
