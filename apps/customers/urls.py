"""
Customer URL configuration.
"""

from django.urls import path

from apps.customers.views import RegisterCustomerView

urlpatterns = [
    path('register', RegisterCustomerView.as_view(), name='register'),
]
