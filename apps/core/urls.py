"""
Core app URL configuration for data ingestion trigger.
"""

from django.urls import path

from apps.core.views import TriggerIngestionView

urlpatterns = [
    path(
        'ingest-data',
        TriggerIngestionView.as_view(),
        name='ingest-data',
    ),
]
