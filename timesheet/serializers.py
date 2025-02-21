from rest_framework import serializers
from .models import Timesheet

class TimesheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timesheet
        fields = ['timesheet_id', 'hours_logged', 'hourly_rate', 'date_logged', 'remarks', 'total_amount']
