# client_new/management/commands/fix_jobcard_client_names.py
from django.core.management.base import BaseCommand
from client_new.models import JobCard

class Command(BaseCommand):
    help = 'Fix client_name field in JobCards'

    def handle(self, *args, **options):
        jobcards = JobCard.objects.select_related('rfq__client').all()
        updated = 0
        
        for jobcard in jobcards:
            if jobcard.rfq and jobcard.rfq.client:
                old_name = jobcard.client_name or "(empty)"
                jobcard.client_name = jobcard.rfq.client.client_name
                jobcard.save(update_fields=['client_name'])
                updated += 1
                self.stdout.write(f"Updated JobCard #{jobcard.job_id}: {old_name} → {jobcard.client_name}")
        
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} JobCards with correct client names"))