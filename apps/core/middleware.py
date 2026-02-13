"""
API Key authentication middleware.

All endpoints except /health/ require a valid API key
in the X-API-KEY header.
"""

import logging

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Paths that don't require authentication
EXEMPT_PATHS = (
    '/health/',
    '/health',
    '/admin/',
)


class APIKeyMiddleware:
    """
    Middleware that checks for a valid API key in the X-API-KEY header.

    If API_KEYS is empty in settings (e.g., during testing), the middleware
    is effectively disabled and all requests pass through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip auth for exempt paths
        if any(request.path.startswith(path) for path in EXEMPT_PATHS):
            return self.get_response(request)

        # If no API keys configured, skip auth (dev/test mode)
        api_keys = getattr(settings, 'API_KEYS', [])
        if not api_keys:
            return self.get_response(request)

        # Check the X-API-KEY header
        provided_key = request.META.get('HTTP_X_API_KEY', '')

        if not provided_key:
            logger.warning(
                "Request to %s rejected: missing API key",
                request.path,
            )
            return JsonResponse(
                {
                    'error': True,
                    'status_code': 401,
                    'detail': 'Authentication required. Provide X-API-KEY header.',
                },
                status=401,
            )

        if provided_key not in api_keys:
            logger.warning(
                "Request to %s rejected: invalid API key",
                request.path,
            )
            return JsonResponse(
                {
                    'error': True,
                    'status_code': 403,
                    'detail': 'Invalid API key.',
                },
                status=403,
            )

        return self.get_response(request)
