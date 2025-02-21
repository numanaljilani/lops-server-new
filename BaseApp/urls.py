from django.contrib import admin 
from django.urls import path, include 
from BaseApp.views import CompanyViewSet,EmployeeViewSet
from rest_framework import routers

router= routers.DefaultRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'employees', EmployeeViewSet)
# router.register(r'list',UserList)
# router.register(r'details',UserDetail)

urlpatterns = [
    path('',include(router.urls))
]