from django_filters import rest_framework as filters
from .models import RFQ, JobCard, Expense


class RFQFilter(filters.FilterSet):
    # Define a filter for `position`
    status = filters.CharFilter(field_name='status', lookup_expr='iexact')
    quotation_number = filters.CharFilter(field_name='quotation_number', lookup_expr='iexact')
    rfq_id = filters.CharFilter(field_name='rfq_id', lookup_expr='iexact')
    # location = filters.CharFilter(field_name='location', lookup_expr='iexact')

    class Meta:
        model = RFQ
        fields = ['status', 'quotation_number', 'rfq_id']


class JobCardFilter(filters.FilterSet):
    # Define a filter for `position`
    status = filters.CharFilter(field_name='status', lookup_expr='iexact')
    project_expense = filters.CharFilter(field_name='project_expense', lookup_expr='iexact')

    class Meta:
        model = JobCard
        fields = ['status', 'project_expense']   




class ExpenseFilter(filters.FilterSet):
    min_date = filters.DateFilter(field_name='date', lookup_expr='gte')
    max_date = filters.DateFilter(field_name='date', lookup_expr='lte')
    min_amount = filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = filters.NumberFilter(field_name='amount', lookup_expr='lte')
    status = filters.CharFilter(field_name='status')
    expense_type = filters.CharFilter(field_name='expense_type')
    supplier = filters.NumberFilter(field_name='supplier')
    
    class Meta:
        model = Expense
        fields = {
            'job_card': ['exact'],
            'category': ['exact'],
            'payment_mode': ['exact'],
        }             