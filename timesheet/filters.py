# timesheet/filters.py
from django_filters import rest_framework as filters
from .models import Timesheet

class TimesheetFilter(filters.FilterSet):
    min_date = filters.DateFilter(field_name='date_logged', lookup_expr='gte')
    max_date = filters.DateFilter(field_name='date_logged', lookup_expr='lte')
    min_hours = filters.NumberFilter(field_name='hours_logged', lookup_expr='gte')
    max_hours = filters.NumberFilter(field_name='hours_logged', lookup_expr='lte')
    
    class Meta:
        model = Timesheet
        fields = {
            'job_card': ['exact'],
            'team_member': ['exact'],
            'date_logged': ['exact']
        }