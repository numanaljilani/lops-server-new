# from django.urls import path
# from .views import TimesheetListCreateView, TimesheetDetailView

# urlpatterns = [
#     path('timesheets/', TimesheetListCreateView.as_view(), name='timesheet-list-create'),
#     path('timesheets/<int:pk>/', TimesheetDetailView.as_view(), name='timesheet-detail'),
# ]

# timesheet/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TimesheetViewSet

router = DefaultRouter()
router.register(r'timesheets', TimesheetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]