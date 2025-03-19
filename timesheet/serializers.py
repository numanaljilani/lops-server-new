# timesheet/serializers.py
from rest_framework import serializers
from .models import Timesheet

class TimesheetSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='team_member.name', read_only=True)
    job_number = serializers.CharField(source='job_card.job_number', read_only=True)
    client_name = serializers.CharField(source='job_card.client_name', read_only=True)
    
    class Meta:
        model = Timesheet
        fields = [
            'timesheet_id', 'job_card', 'job_number', 'client_name',
            'team_member', 'employee_name', 'hours_logged', 
            'hourly_rate', 'date_logged', 'remarks', 
            'total_amount', 
        ]
        read_only_fields = ['total_amount', 'created_at', 'updated_at']
    
    def validate(self, data):
        # If hourly_rate is not provided, get it from employee
        if 'hourly_rate' not in data and 'team_member' in data:
            data['hourly_rate'] = data['team_member'].hourly_rate
            
        # Validate hours_logged
        if data.get('hours_logged', 0) <= 0:
            raise serializers.ValidationError(
                {"hours_logged": "Hours logged must be greater than 0"}
            )
            
        return data