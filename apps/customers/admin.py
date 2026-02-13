from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'first_name', 'last_name', 'age',
        'phone_number', 'monthly_salary', 'approved_limit',
        'current_debt', 'created_at',
    )
    list_filter = ('age', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
