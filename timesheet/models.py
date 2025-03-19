# timesheet/models.py
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Timesheet(models.Model):
    timesheet_id = models.AutoField(primary_key=True)
    job_card = models.ForeignKey('client_new.JobCard', on_delete=models.CASCADE, related_name='timesheets')
    team_member = models.ForeignKey('BaseApp.Employee', on_delete=models.CASCADE, related_name='timesheets')
    hours_logged = models.DecimalField(max_digits=5, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    date_logged = models.DateField(default=timezone.now)
    remarks = models.TextField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    

    class Meta:
        ordering = ['-date_logged', ]

    def save(self, *args, **kwargs):
        # Get hourly rate from employee if not provided
        if not self.hourly_rate and self.team_member:
            self.hourly_rate = self.team_member.hourly_rate
            
        self.total_amount = self.hours_logged * self.hourly_rate
        super().save(*args, **kwargs)
        
        # Update employee totals
        self.team_member.update_timesheet_totals()
        
        # Update job card financials
        if self.job_card:
            self.job_card.update_project_financials()

    def delete(self, *args, **kwargs):
        job_card = self.job_card
        team_member = self.team_member
        super().delete(*args, **kwargs)
        
        # Update related objects after deletion
        if team_member:
            team_member.update_timesheet_totals()
        if job_card:
            job_card.update_project_financials()