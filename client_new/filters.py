from django_filters import rest_framework as filters
from .models import RFQ, JobCard

class RFQFilter(filters.FilterSet):
    # Define a filter for `position`
    status = filters.CharFilter(field_name='status', lookup_expr='iexact')
    # location = filters.CharFilter(field_name='location', lookup_expr='iexact')

    class Meta:
        model = RFQ
        fields = ['status']


class JobCardFilter(filters.FilterSet):
    # Define a filter for `position`
    status = filters.CharFilter(field_name='status', lookup_expr='iexact')
    project_expense = filters.CharFilter(field_name='project_expense', lookup_expr='iexact')

    class Meta:
        model = JobCard
        fields = ['status', 'project_expense']        