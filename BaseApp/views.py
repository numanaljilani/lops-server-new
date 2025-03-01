from django.shortcuts import render 
from rest_framework import viewsets 
from BaseApp.models import Company,Employee
from BaseApp.serializers import CompanySerializer,EmployeeSerializer,UserSerializer
from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend  # Add this import
from .filters import EmployeeFilter, CompanyFilter  # Import the filter
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter

from rest_framework.pagination import PageNumberPagination
from .pagination import CustomPagination
from rest_framework.response import Response
from django.core.paginator import EmptyPage



class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer 
    permission_classes = [AllowAny]

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]



   

# Create your views here.
class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.order_by('added_date').all()  # Default ascending order by date
    serializer_class = CompanySerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['added_date', 'name', 'location', 'type']  # Reordered to show date first
    ordering = ['added_date']  # Default ordering

    def get_queryset(self):
        queryset = Company.objects.all()
        
        # Get ordering parameter from request
        order_by = self.request.query_params.get('order_by', 'added_date')  # Default to 'added_date'
        order_direction = self.request.query_params.get('direction', 'asc')  # Default to ascending
        
        # Apply ordering
        if order_direction == 'desc':
            order_by = f'-{order_by}'
        
        return queryset.order_by(order_by)

    @action(detail=False, methods=['get'])
    def ascending(self, request):
        """Get companies in ascending order"""
        field = request.query_params.get('field', 'added_date')  # Default to date
        queryset = self.get_queryset().order_by(field)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def descending(self, request):
        """Get companies in descending order"""
        field = request.query_params.get('field', 'added_date')  # Default to date
        queryset = self.get_queryset().order_by(f'-{field}')
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get page number from query params
        page = request.query_params.get('page', 1)
        
        try:
            page_number = int(page)
            paginator = self.pagination_class()
            
            try:
                page_obj = paginator.paginate_queryset(queryset, request)
                serializer = self.get_serializer(page_obj, many=True)
                return paginator.get_paginated_response(serializer.data)
            except EmptyPage:
                return Response({
                    'error': f'Page {page_number} does not exist. Total pages: {paginator.page.paginator.num_pages}'
                }, status=404)
                
        except ValueError:
            return Response({
                'error': 'Invalid page number'
            }, status=400)

    @action(detail=False, methods=['get'])
    def page_info(self, request):
        """Get information about available pages"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page_size = paginator.get_page_size(request)
        
        return Response({
            'total_items': queryset.count(),
            'page_size': page_size,
            'total_pages': (queryset.count() + page_size - 1) // page_size
        }) 

class EmployeeViewSet(viewsets.ModelViewSet):
    # permission_classes = [IsAuthenticated]
    queryset= Employee.objects.order_by('-created_at').all()
    serializer_class=EmployeeSerializer

    # Enable filter backend and specify the filterset class
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmployeeFilter

# Create your views here.
# def home (index) :
#     return HttpResponse("This is home page")

# def test(index) :
#     return HttpResponse("This is test page")