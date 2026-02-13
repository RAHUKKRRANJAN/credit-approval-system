from django.contrib import admin

from apps.loans.models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'loan_amount', 'tenure',
        'interest_rate', 'monthly_installment',
        'emis_paid_on_time', 'is_active', 'start_date', 'end_date',
    )
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('customer__first_name', 'customer__last_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('customer',)
