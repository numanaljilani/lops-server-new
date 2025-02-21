from django.db import models
from django.utils import timezone

class Timesheet(models.Model):
    timesheet_id = models.AutoField(primary_key=True)
    job_card = models.ForeignKey('client_new.JobCard', on_delete=models.CASCADE)
    team_member = models.ForeignKey('BaseApp.Employee', on_delete=models.CASCADE)
    hours_logged = models.DecimalField(max_digits=5, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    date_logged = models.DateField(default=timezone.now)
    remarks = models.TextField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.total_amount = self.hours_logged * self.hourly_rate
        super().save(*args, **kwargs)
        self.team_member.update_timesheet_totals()