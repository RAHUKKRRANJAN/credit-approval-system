"""
Customer views for the Credit Approval System.

Views are thin — all business logic is in the service layer.
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.serializers import (
    CustomerResponseSerializer,
    RegisterCustomerSerializer,
)
from apps.customers.services import CustomerService

logger = logging.getLogger(__name__)


class RegisterCustomerView(APIView):
    """
    POST /api/register

    Register a new customer in the system.
    """

    def post(self, request):
        """Handle customer registration."""
        serializer = RegisterCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = CustomerService.register(serializer.validated_data)

        response_data = {
            'customer_id': customer.pk,
            'name': customer.full_name,
            'age': customer.age,
            'monthly_income': customer.monthly_salary,
            'approved_limit': customer.approved_limit,
            'phone_number': customer.phone_number,
        }

        response_serializer = CustomerResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(
            response_serializer.validated_data,
            status=status.HTTP_201_CREATED,
        )
