# timesheet/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from .models import Timesheet
from .serializers import TimesheetSerializer
from .filters import TimesheetFilter

class TimesheetViewSet(viewsets.ModelViewSet):
    queryset = Timesheet.objects.all()
    serializer_class = TimesheetSerializer
    filterset_class = TimesheetFilter
    
    def get_queryset(self):
        return Timesheet.objects.select_related('job_card', 'team_member')
    
    @action(detail=False, methods=['get'])
    def by_job_card(self, request):
        """Get timesheets for a specific job card with summary"""
        job_card_id = request.query_params.get('job_card')
        if not job_card_id:
            return Response({"error": "job_card parameter is required"}, status=400)
            
        timesheets = self.filter_queryset(
            self.get_queryset().filter(job_card_id=job_card_id)
        )
        
        # Calculate totals
        total_hours = timesheets.aggregate(total=Sum('hours_logged'))['total'] or 0
        total_amount = timesheets.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Employee breakdown
        employee_breakdown = timesheets.values(
            'team_member', 'team_member__name'
        ).annotate(
            hours=Sum('hours_logged'),
            amount=Sum('total_amount'),
            count=Count('timesheet_id')
        ).order_by('-hours')
        
        # Date breakdown (by month)
        from django.db.models.functions import TruncMonth
        date_breakdown = timesheets.annotate(
            month=TruncMonth('date_logged')
        ).values('month').annotate(
            hours=Sum('hours_logged'),
            amount=Sum('total_amount'),
            count=Count('timesheet_id')
        ).order_by('month')
        
        # Paginate the timesheets
        page = self.paginate_queryset(timesheets)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['summary'] = {
                'total_hours': float(total_hours),
                'total_amount': float(total_amount),
                'count': timesheets.count(),
                'employee_breakdown': employee_breakdown,
                'date_breakdown': date_breakdown
            }
            return response
            
        serializer = self.get_serializer(timesheets, many=True)
        return Response({
            'timesheets': serializer.data,
            'summary': {
                'total_hours': float(total_hours),
                'total_amount': float(total_amount),
                'count': timesheets.count(),
                'employee_breakdown': employee_breakdown,
                'date_breakdown': date_breakdown
            }
        })
        
    @action(detail=False, methods=['get'])
    def by_employee(self, request):
        """Get timesheets for a specific employee with summary"""
        employee_id = request.query_params.get('team_member')
        if not employee_id:
            return Response({"error": "team_member parameter is required"}, status=400)
            
        timesheets = self.filter_queryset(
            self.get_queryset().filter(team_member_id=employee_id)
        )
        
        # Calculate totals
        total_hours = timesheets.aggregate(total=Sum('hours_logged'))['total'] or 0
        total_amount = timesheets.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Job card breakdown
        job_breakdown = timesheets.values(
            'job_card', 'job_card__job_number', 'job_card__client_name'
        ).annotate(
            hours=Sum('hours_logged'),
            amount=Sum('total_amount'),
            count=Count('timesheet_id')
        ).order_by('-hours')
        
        # Date breakdown (by month)
        from django.db.models.functions import TruncMonth
        date_breakdown = timesheets.annotate(
            month=TruncMonth('date_logged')
        ).values('month').annotate(
            hours=Sum('hours_logged'),
            amount=Sum('total_amount'),
            count=Count('timesheet_id')
        ).order_by('month')
        
        # Paginate the timesheets
        page = self.paginate_queryset(timesheets)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['summary'] = {
                'total_hours': float(total_hours),
                'total_amount': float(total_amount),
                'count': timesheets.count(),
                'job_breakdown': job_breakdown,
                'date_breakdown': date_breakdown
            }
            return response
            
        serializer = self.get_serializer(timesheets, many=True)
        return Response({
            'timesheets': serializer.data,
            'summary': {
                'total_hours': float(total_hours),
                'total_amount': float(total_amount),
                'count': timesheets.count(),
                'job_breakdown': job_breakdown,
                'date_breakdown': date_breakdown
            }
        })