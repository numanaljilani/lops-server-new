# BaseApp/filters.py
from django_filters import rest_framework as filters
from .models import Employee, Company

class EmployeeFilter(filters.FilterSet):
    # Define a filter for `position`
    position = filters.CharFilter(field_name='position', lookup_expr='iexact')
    location = filters.CharFilter(field_name='location', lookup_expr='iexact')

    class Meta:
        model = Employee
        fields = ['position', 'location']


class CompanyFilter(filters.FilterSet):
    # Define a filter for `position`
    name = filters.CharFilter(field_name='name', lookup_expr='iexact')
    # position = filters.CharFilter(field_name='position', lookup_expr='iexact')
    location = filters.CharFilter(field_name='location', lookup_expr='iexact')

    class Meta:
        model = Company
        fields = ['name', 'location']        
