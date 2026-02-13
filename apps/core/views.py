"""
Core views for the Credit Approval System.
"""

import logging

from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.tasks import ingest_customer_data, ingest_loan_data

logger = logging.getLogger(__name__)


def health_check(request):
    """
    GET /health/

    Simple health check endpoint for Docker and load balancer probes.
    Exempt from API key authentication.
    """
    return JsonResponse({'status': 'healthy'}, status=200)


class TriggerIngestionView(APIView):
    """
    POST /api/ingest-data

    Trigger background ingestion of customer and loan data
    from Excel files via Celery tasks.
    """

    def post(self, request):
        """Trigger data ingestion tasks."""
        customer_task = ingest_customer_data.delay()
        loan_task = ingest_loan_data.delay()

        logger.info(
            "Data ingestion triggered — customer_task=%s, loan_task=%s",
            customer_task.id,
            loan_task.id,
        )

        return Response(
            {
                'message': 'Data ingestion tasks have been triggered.',
                'customer_task_id': customer_task.id,
                'loan_task_id': loan_task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )
