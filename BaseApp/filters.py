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


# BaseApp/filters.py

class CompanyFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    location = filters.CharFilter(field_name='location', lookup_expr='icontains')
    type = filters.CharFilter(field_name='type', lookup_expr='exact')
    active = filters.BooleanFilter(field_name='active')
    order_by = filters.ChoiceFilter(
        choices=[
            ('added_date', 'Date Added'),  # Put date first
            ('name', 'Name'),
            ('location', 'Location'),
            ('type', 'Type')
        ],
        method='filter_order_by'
    )
    direction = filters.ChoiceFilter(
        choices=[
            ('asc', 'Ascending'),
            ('desc', 'Descending')
        ],
        method='filter_direction'
    )

    class Meta:
        model = Company
        fields = ['name', 'location', 'type', 'active', 'order_by', 'direction']

    def filter_order_by(self, queryset, name, value):
        direction = self.data.get('direction', 'asc')
        order_by = value if direction == 'asc' else f'-{value}'
        return queryset.order_by(order_by)

    def filter_direction(self, queryset, name, value):
        order_by = self.data.get('order_by', 'added_date')  # Default to added_date
        if value == 'desc':
            order_by = f'-{order_by}'
        return queryset.order_by(order_by) 
