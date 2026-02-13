"""
Loan views for the Credit Approval System.

Views are thin — all business logic is in the service layer.
"""

import logging

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import CustomerNotFoundError, LoanNotFoundError
from apps.customers.models import Customer
from apps.loans.serializers import (
    CheckEligibilitySerializer,
    CreateLoanResponseSerializer,
    CreateLoanSerializer,
    EligibilityResponseSerializer,
    ViewLoanResponseSerializer,
    ViewLoansItemSerializer,
)
from apps.loans.services import EligibilityService, LoanService

logger = logging.getLogger(__name__)


class CheckEligibilityView(APIView):
    """
    POST /api/check-eligibility

    Check if a customer is eligible for a loan.
    """

    def post(self, request):
        """Handle eligibility check."""
        serializer = CheckEligibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Fetch customer for eligibility check
        customer_id = serializer.validated_data['customer_id']
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            raise CustomerNotFoundError(
                detail=f"Customer with ID {customer_id} not found."
            )

        result = EligibilityService.check(
            customer=customer,
            loan_amount=serializer.validated_data['loan_amount'],
            interest_rate=serializer.validated_data['interest_rate'],
            tenure=serializer.validated_data['tenure'],
        )

        response_serializer = EligibilityResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        return Response(
            response_serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class CreateLoanView(APIView):
    """
    POST /api/create-loan

    Process a new loan application.
    """

    def post(self, request):
        """Handle loan creation."""
        serializer = CreateLoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = LoanService.create_loan(
            customer_id=serializer.validated_data['customer_id'],
            loan_amount=serializer.validated_data['loan_amount'],
            interest_rate=serializer.validated_data['interest_rate'],
            tenure=serializer.validated_data['tenure'],
        )

        response_serializer = CreateLoanResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        if result['loan_approved']:
            http_status = status.HTTP_201_CREATED
        else:
            http_status = status.HTTP_200_OK

        return Response(
            response_serializer.validated_data,
            status=http_status,
        )


class ViewLoanView(APIView):
    """
    GET /api/view-loan/<loan_id>

    View details of a specific loan with customer information.
    """

    def get(self, request, loan_id):
        """Handle viewing a single loan."""
        loan = LoanService.get_loan(loan_id)

        if loan is None:
            raise LoanNotFoundError(
                detail=f"Loan with ID {loan_id} not found."
            )

        response_data = {
            'loan_id': loan.pk,
            'customer': {
                'id': loan.customer.pk,
                'first_name': loan.customer.first_name,
                'last_name': loan.customer.last_name,
                'phone_number': loan.customer.phone_number,
                'age': loan.customer.age,
            },
            'loan_amount': loan.loan_amount,
            'interest_rate': loan.interest_rate,
            'monthly_installment': loan.monthly_installment,
            'tenure': loan.tenure,
        }

        response_serializer = ViewLoanResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(
            response_serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class LoanPagination(PageNumberPagination):
    """Pagination for customer loan list."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ViewLoansView(APIView):
    """
    GET /api/view-loans/<customer_id>

    View all loans for a specific customer, with pagination.
    """

    def get(self, request, customer_id):
        """Handle viewing all loans for a customer."""
        loans = LoanService.get_customer_loans(customer_id)

        # Paginate
        paginator = LoanPagination()
        page = paginator.paginate_queryset(loans, request)

        if page is not None:
            response_data = []
            for loan in page:
                item = {
                    'loan_id': loan.pk,
                    'loan_amount': loan.loan_amount,
                    'interest_rate': loan.interest_rate,
                    'monthly_installment': loan.monthly_installment,
                    'repayments_left': loan.repayments_left,
                }
                response_data.append(item)

            serializer = ViewLoansItemSerializer(data=response_data, many=True)
            serializer.is_valid(raise_exception=True)

            return paginator.get_paginated_response(serializer.validated_data)

        # Fallback if no pagination needed
        response_data = []
        for loan in loans:
            item = {
                'loan_id': loan.pk,
                'loan_amount': loan.loan_amount,
                'interest_rate': loan.interest_rate,
                'monthly_installment': loan.monthly_installment,
                'repayments_left': loan.repayments_left,
            }
            response_data.append(item)

        serializer = ViewLoansItemSerializer(data=response_data, many=True)
        serializer.is_valid(raise_exception=True)

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )
