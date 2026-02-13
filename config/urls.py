"""
URL configuration for Credit Approval System.
"""

from django.contrib import admin
from django.urls import include, path

from apps.core.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('api/', include('apps.customers.urls')),
    path('api/', include('apps.loans.urls')),
    path('api/', include('apps.core.urls')),
]
