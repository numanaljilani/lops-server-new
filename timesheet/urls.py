from django.urls import path
from .views import TimesheetListCreateView, TimesheetDetailView

urlpatterns = [
    path('timesheets/', TimesheetListCreateView.as_view(), name='timesheet-list-create'),
    path('timesheets/<int:pk>/', TimesheetDetailView.as_view(), name='timesheet-detail'),
]
