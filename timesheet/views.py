from rest_framework import generics
from .models import Timesheet
from .serializers import TimesheetSerializer

class TimesheetListCreateView(generics.ListCreateAPIView):
    queryset = Timesheet.objects.all()
    serializer_class = TimesheetSerializer

class TimesheetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Timesheet.objects.all()
    serializer_class = TimesheetSerializer
