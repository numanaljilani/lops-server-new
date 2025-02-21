from django.shortcuts import render 
from rest_framework import viewsets 
from BaseApp.models import Company,Employee
from BaseApp.serializers import CompanySerializer,EmployeeSerializer,UserSerializer
from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend  # Add this import
from .filters import EmployeeFilter, CompanyFilter  # Import the filter

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
    # permission_classes = [IsAuthenticated]
    queryset= Company.objects.order_by('-added_date').all()
    serializer_class=CompanySerializer

    # Enable filter backend and specify the filterset class
    filter_backends = [DjangoFilterBackend]
    filterset_class = CompanyFilter

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