from django.db import models
from timesheet.models import Timesheet

# Create your models here.
#Company Model
class Company(models.Model):
    company_id=models.AutoField(primary_key=True)
    name= models.CharField(max_length=50)
    location=models.CharField(max_length=50) 
    about=models.TextField()
    type=models.CharField(max_length=100, choices=(('Consultancy Services','Consultancy Services'),
                                                    ('General Contracting','General Contracting'),
                                                    ('Electro-Mechanical Works','Electro-Mechanical Works'),
                                                    ('Design & Drafting Services','Design & Drafting Services'),
                                                    ('IT Solutions','IT Solutions'),
                                                    ('Video Production Services','Video Production Services'),
                                                    ))
    added_date=models.DateTimeField(auto_now=True)
    active=models.BooleanField(default=True)
    

    def __str__(self):
        return self.name
    

#Employee Models

# class Employee(models.Model):
#     # id = models.models.ForeignKey("app.Model", verbose_name=_(""), on_delete=models.CASCADE)
#     name = models.CharField(max_length=50)
#     email = models.CharField(max_length=50)
#     location=models.CharField(max_length=50)
#     position=models.CharField(max_length=100, choices=(('Sales Member','Sales Member'),
#                                                     ('Team Leads','Team Leads'),
#                                                     ('Team Members','Team Members'),
#                                                     ('Sub-Contractors','Sub-Contractors'),
#                                                     ('Accounts Members','Accounts Members')))
#     added_date=models.DateTimeField(auto_now=True)
#     active=models.BooleanField(default=True)
#     companyf = models.ForeignKey(Company,on_delete=models.CASCADE)

#     def __str__(self):
#         return self.name



class Employee(models.Model):

    CURRENCY_CHOICES = [
        ('AED', 'AED'),
        ('USD', 'USD'),
        ('INR', 'INR'),
        ('SAR', 'SAR'),
    ]

    DESIGNATION_CHOICES = [
        ('Sales Member', 'Sales Member'),
        ('Team Leads', 'Team Leads'),
        ('Team Members', 'Team Members'),
        ('Sub-Contractors', 'Sub-Contractors'),
        ('Accountant Members', 'Accountant Members'),
    ]

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    contact = models.CharField(max_length=20)
    description = models.TextField()
    location = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="employees")
    position = models.CharField(max_length=50, choices=DESIGNATION_CHOICES)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='AED')
    status = models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now=True)
    total_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} - {self.position} at {self.company.name}"

    def save(self, *args, **kwargs):
        # Automatically calculate hourly rate based on salary
        self.hourly_rate = self.salary / 207
        super().save(*args, **kwargs)

    def update_timesheet_totals(self):
        from timesheet.models import Timesheet
        timesheets = Timesheet.objects.filter(team_member=self)
        self.total_hours = sum(t.hours_logged for t in timesheets)
        self.amount = sum(t.total_amount for t in timesheets)
        self.save()    