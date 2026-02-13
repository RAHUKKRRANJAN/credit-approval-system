"""
Loan serializers for the Credit Approval System.
"""

from decimal import Decimal

from rest_framework import serializers


class CheckEligibilitySerializer(serializers.Serializer):
    """Serializer for eligibility check request."""

    customer_id = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="Customer's ID.",
    )
    loan_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=True,
        help_text="Requested loan amount.",
    )
    interest_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        required=True,
        help_text="Requested annual interest rate (%).",
    )
    tenure = serializers.IntegerField(
        min_value=1,
        max_value=360,
        required=True,
        help_text="Loan tenure in months.",
    )


class EligibilityResponseSerializer(serializers.Serializer):
    """Serializer for eligibility check response."""

    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=15, decimal_places=2)


class CreateLoanSerializer(serializers.Serializer):
    """Serializer for loan creation request."""

    customer_id = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="Customer's ID.",
    )
    loan_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=True,
        help_text="Requested loan amount.",
    )
    interest_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        required=True,
        help_text="Requested annual interest rate (%).",
    )
    tenure = serializers.IntegerField(
        min_value=1,
        max_value=360,
        required=True,
        help_text="Loan tenure in months.",
    )


class CreateLoanResponseSerializer(serializers.Serializer):
    """Serializer for loan creation response."""

    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.DecimalField(
        max_digits=15, decimal_places=2, allow_null=True,
    )


class ViewLoanResponseSerializer(serializers.Serializer):
    """Serializer for single loan view response."""

    loan_id = serializers.IntegerField()
    customer = serializers.DictField()
    loan_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    monthly_installment = serializers.DecimalField(max_digits=15, decimal_places=2)
    tenure = serializers.IntegerField()


class ViewLoansItemSerializer(serializers.Serializer):
    """Serializer for individual loan item in customer's loan list."""

    loan_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    monthly_installment = serializers.DecimalField(max_digits=15, decimal_places=2)
    repayments_left = serializers.IntegerField()
