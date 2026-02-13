"""
Custom exceptions and DRF exception handler for the Credit Approval System.
"""

import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class CustomerNotFoundError(APIException):
    """Raised when a customer does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Customer not found.'
    default_code = 'customer_not_found'


class LoanNotFoundError(APIException):
    """Raised when a loan does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Loan not found.'
    default_code = 'loan_not_found'


class LoanNotApprovedError(APIException):
    """Raised when a loan is not approved after eligibility check."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Loan not approved.'
    default_code = 'loan_not_approved'


class DataIngestionError(Exception):
    """Raised when data ingestion fails."""

    pass


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns consistent error responses.

    Handles all DRF exceptions and adds logging for server errors.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'error': True,
            'status_code': response.status_code,
            'detail': response.data,
        }
        response.data = error_data
    else:
        # Unhandled exceptions — log and return 500
        logger.exception(
            "Unhandled exception in %s",
            context.get('view', 'unknown'),
            exc_info=exc,
        )
        response = Response(
            {
                'error': True,
                'status_code': 500,
                'detail': 'An unexpected error occurred. Please try again later.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
