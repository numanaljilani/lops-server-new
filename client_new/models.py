from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json, uuid
from decimal import Decimal
from BaseApp.models import Company, Employee
from timesheet.models import Timesheet
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone


PERCENTAGE_VALIDATOR = [MinValueValidator(0), MaxValueValidator(100)]

class Client(models.Model):
    client_id = models.AutoField(primary_key=True)
    client_name = models.CharField(max_length=255)
    contact_info = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255)  # Changed `name` to `company`
    service = models.CharField(
        max_length=100,
        choices=Company._meta.get_field('type').choices,
        blank=True,
        null=True
    )
    about = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    aob = models.TextField(blank=True, null=True)  # Area of Business
    contact_person = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)

    def __str__(self):
        return self.client_name


class RFQ(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
    ]

    rfq_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="rfqs")
    rfq_date = models.DateTimeField(auto_now_add=True)
    project_type = models.CharField(max_length=255)
    scope_of_work = models.TextField()
    quotation_number = models.CharField(max_length=20, unique=True)
    quotation_amount = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)
    

    def __str__(self):
        return f"RFQ for {self.client.client_name} - {self.project_type}"


class JobCard(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
    ]

    STATUS_C_CHOICES = [
        ('gray', 'Gray'),
        ('blue', 'Blue'),
        ('purple', 'Purple'),
        ('pink', 'Pink'),
        ('green', 'Green'),
    ]

    job_id = models.AutoField(primary_key=True)
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="job_cards")
    job_number = models.CharField(max_length=20, unique=True)
    scope_of_work = models.TextField()
    delivery_timelines = models.DateField()
    payment_terms = models.TextField(blank=True, null=True) 
    status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True) # new field

    color_status = models.CharField(max_length=6, choices=STATUS_C_CHOICES, default='gray')
  # New standardized job number
    client_name = models.CharField(max_length=255, editable=False)  # Will be auto-filled
    
    completion_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=PERCENTAGE_VALIDATOR
    )
    project_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_timesheet_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def update_project_financials(self):
        """Update project financial calculations"""
        # Calculate total approved expenses
        approved_expenses = self.expenses.filter(status='Approved')
        self.total_expenses = sum(expense.amount for expense in approved_expenses)

        # Calculate total timesheet cost
        
        timesheets = Timesheet.objects.filter(job_card=self)
        self.total_timesheet_cost = sum(
            timesheet.hours_logged * timesheet.hourly_rate 
            for timesheet in timesheets
        )

        # Calculate profit
        if self.rfq:
            total_cost = self.total_expenses + self.total_timesheet_cost
            self.profit = self.rfq.quotation_amount - total_cost

        # Save only the financial fields
        self.save(update_fields=['total_expenses', 'total_timesheet_cost', 'profit'])

    def save(self, *args, **kwargs):
        # Auto-fill client name
        if self.rfq:
            self.client_name = self.rfq.client.client_name

        # Calculate profit
        if self.rfq and self.project_expense:
            self.profit = self.rfq.quotation_amount - self.project_expense

        # First save to get the primary key
        super().save(*args, **kwargs)

        # Only calculate completion percentage if the instance has been saved (has pk)
        if self.pk:
            total_completion = 0
            total_weight = 0
            
            payment_balls = self.payment_balls.all()
            if payment_balls.exists():
                for payment_ball in payment_balls:
                    tasks = payment_ball.tasks.all()
                    if tasks:
                        ball_completion = sum(
                            task.completion_percentage * task.weightage / 100 
                            for task in tasks
                        )
                        total_completion += ball_completion * payment_ball.project_percentage / 100
                        total_weight += payment_ball.project_percentage

                if total_weight > 0:
                    self.completion_percentage = total_completion
                    # Save again only if completion percentage changed
                    super().save(update_fields=['completion_percentage'])


    def get_payment_terms(self):
        if not self.payment_terms:
            return {}  # Return empty dict instead of list
        
        try:
            terms = json.loads(self.payment_terms)
            return {
                str(i): {
                    'milestone': term['milestone'],
                    'percentage': term['percentage'],
                    'description': term.get('description', '')
                }
                for i, term in enumerate(terms, 1)
            }
        except json.JSONDecodeError:
            return {}

    def set_payment_terms(self, payment_terms):
        if payment_terms is None:
            self.payment_terms = None
            return

        if isinstance(payment_terms, dict):
            # Convert dict to list for storage
            terms_list = [
                {
                    'milestone': data['milestone'],
                    'percentage': float(data['percentage']),
                    'description': data.get('description', '')
                }
                for data in payment_terms.values()
            ]
            self.payment_terms = json.dumps(terms_list, cls=DjangoJSONEncoder)
        else:
            self.payment_terms = json.dumps(payment_terms, cls=DjangoJSONEncoder)

        


class PaymentBall(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('InProgress', 'InProgress'),
        ('Completed', 'Completed'),
    ]

    STATUS_C_CHOICES = [
        ('gray', 'Gray'),
        ('blue', 'Blue'),
        ('purple', 'Purple'),
        ('pink', 'Pink'),
        ('green', 'Green'),
    ]

    VERIFICATION_STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('verified', 'Verified'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid')
    ]

    payment_id = models.AutoField(primary_key=True)
    job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="payment_balls")
    project_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=PERCENTAGE_VALIDATOR,
        null=False  # Make this required
    )
    project_status = models.CharField(
        max_length=50, 
        default='Pending', 
        choices=PAYMENT_STATUS_CHOICES,
        null=False
    )
    notes = models.TextField(blank=True, null=True)
    color_status = models.CharField(
        max_length=6, 
        choices=STATUS_C_CHOICES, 
        default='gray',
        null=False
    )
    invoice_number = models.CharField(max_length=20, blank=True, null=True)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=False  # Make this required
    )
    payment_terms = models.TextField(blank=True, null=True)  # Add this field

    # New fields for accounts team
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='unverified'
    )
    verified_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='verified_payments'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    payment_received_date = models.DateTimeField(null=True, blank=True)
    invoice_number = models.CharField(max_length=20, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    def verify_completion(self, verified_by):
        if self.project_status == 'Completed' and self.verification_status == 'unverified':
            self.verification_status = 'verified'
            self.verified_by = verified_by
            self.verification_date = timezone.now()
            self.color_status = 'purple'
            self.save()
            return True
        return False

    def mark_as_invoiced(self):
        if self.verification_status == 'verified':
            self.verification_status = 'invoiced'
            self.color_status = 'pink'
            if not self.invoice_number:
                self.invoice_number = f"INV-{uuid.uuid4().hex[:6].upper()}"
            self.save()
            return True
        return False

    def mark_as_paid(self):
        if self.verification_status == 'invoiced':
            self.verification_status = 'paid'
            self.payment_received_date = timezone.now()
            self.color_status = 'green'
            self.save()
            return True
        return False
    

    def generate_invoice(self):
        if self.color_status == 'purple' and not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:6].upper()}"
            self.save()

    def __str__(self):
        return f"PaymentBall {self.payment_id} - {self.project_percentage}% for JobCard {self.job_card.job_number}"

    def get_payment_terms(self):
        if not self.payment_terms:
            return []
        try:
            return json.loads(self.payment_terms)
        except json.JSONDecodeError:
            return []

    def set_payment_terms(self, payment_terms):
        if payment_terms is None:
            self.payment_terms = None
            return

        if isinstance(payment_terms, str):
            self.payment_terms = payment_terms
        else:
            self.payment_terms = json.dumps(payment_terms, cls=DjangoJSONEncoder) 

class Task(models.Model):
    TASK_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('InProgress', 'InProgress'),
        ('Completed', 'Completed'),
    ]

    task_id = models.AutoField(primary_key=True)
    payment_ball = models.ForeignKey(PaymentBall, on_delete=models.CASCADE, related_name="tasks")
    task_brief = models.TextField()
    weightage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=PERCENTAGE_VALIDATOR
    )
    status = models.CharField(
        max_length=50, 
        default='Pending', 
        choices=TASK_STATUS_CHOICES
    )
    due_date = models.DateField()
    assignee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_tasks'
    )
    remarks = models.TextField(blank=True, null=True)
    completion_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        validators=PERCENTAGE_VALIDATOR
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Task {self.task_id} for PaymentBall {self.payment_ball.payment_id}"

    class Meta:
        ordering = ['-created_at']
    

class SubContracting(models.Model):
    SUBCONTRACT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('InProgress', 'InProgress'),
        ('Completed', 'Completed'),
    ]

    subcontract_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="subcontracts")
    subcontract_brief = models.TextField()
    weightage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=PERCENTAGE_VALIDATOR
    )
    status = models.CharField(
        max_length=50, 
        default='Pending', 
        choices=SUBCONTRACT_STATUS_CHOICES
    )
    due_date = models.DateField()
    assignee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_subcontracts'
    )
    remarks = models.TextField(blank=True, null=True)
    completion_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        validators=PERCENTAGE_VALIDATOR
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SubContracting {self.subcontract_id} for Task {self.task.task_id}"

    class Meta:
        ordering = ['-created_at']            


# client_new/models.py

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Expense Categories"

class Expense(models.Model):
    EXPENSE_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    EXPENSE_TYPE_CHOICES = [
        ('Material', 'Material'),
        ('Labor', 'Labor'),
        ('Equipment', 'Equipment'),
        ('Transportation', 'Transportation'),
        ('Subcontractor', 'Subcontractor'),
        ('Other', 'Other'),
    ]

    expense_id = models.AutoField(primary_key=True)
    job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=EXPENSE_STATUS_CHOICES, default='Pending')
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # urls field 

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Expense {self.expense_id} - {self.job_card.job_number} - {self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.job_card.update_project_financials()        

    















# from django.db import models
# from BaseApp.models import Company, Employee
# import json, uuid
# # from django.db.models.signals import pre_save 
# # from django.dispatch import receiver

# class Client(models.Model):
#     client_id = models.AutoField(primary_key=True)
#     client_name = models.CharField(max_length=255)
#     contact_info = models.CharField(max_length=255, blank=True, null=True)
#     company_name = models.CharField(max_length=255)  # Changed `name` to `company`
#     service = models.CharField(
#         max_length=100,
#         choices=Company._meta.get_field('type').choices,
#         blank=True,
#         null=True
#     )
#     about = models.TextField(blank=True, null=True)
#     status = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.client_name
    
    


# class RFQ(models.Model):
#     STATUS_CHOICES = [
#         ('Pending', 'Pending'),
#         ('Ongoing', 'Ongoing'),
#         ('Completed', 'Completed'),
#     ]


#     rfq_id = models.AutoField(primary_key=True)
#     client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="rfqs")  # Changed `client_id` to `client`
#     rfq_date = models.DateTimeField(auto_now_add=True)
#     project_type = models.CharField(max_length=255)
#     scope_of_work = models.TextField()
#     quotation_number = models.CharField(max_length=20, unique=True)
#     quotation_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     remarks = models.TextField(blank=True, null=True)
#     status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)

#     def __str__(self):
#         return f"RFQ for {self.client.client_name} - {self.project_type}"   
    



# class JobCard(models.Model):
#     STATUS_CHOICES = [
#         ('Pending', 'Pending'),
#         ('Ongoing', 'Ongoing'),
#         ('Completed', 'Completed'),
#     ]

#     STATUS_CHOICES = [
#         ('gray', 'Gray'),
#         ('blue', 'Blue'),
#         ('purple', 'Purple'),
#         ('pink', 'Pink'),
#         ('green', 'Green'),
#     ]

#     job_id = models.AutoField(primary_key=True)
#     rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="job_cards")
#     job_number = models.CharField(max_length=20, unique=True)
#     scope_of_work = models.TextField()
#     delivery_timelines = models.DateField()
#     payment_terms = models.TextField()  # Storing payment terms as JSON string
#     status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)
#     created_at = models.DateTimeField(auto_now_add=True) # new field


    
#     status = models.CharField(max_length=6, choices=STATUS_CHOICES, default='gray')
    

#     def update_status(self):
#         """Update the status of the JobCard based on the statuses of its associated PaymentBalls."""
#         statuses = self.payment_balls.values_list('status', flat=True)
#         if all(status == 'green' for status in statuses):
#             self.status = 'green'
#         elif any(status == 'pink' for status in statuses):
#             self.status = 'pink'
#         elif any(status == 'purple' for status in statuses):
#             self.status = 'purple'
#         elif any(status == 'blue' for status in statuses):
#             self.status = 'blue'
#         else:
#             self.status = 'gray'
#         self.save()

#     def __str__(self):
#         return f"JobCard {self.job_number} - Status: {self.get_status_display()}"


#     def __str__(self): 
#         return f"JobCard {self.job_number} - {self.rfq.client.client_name}" 
    
#     def set_payment_terms(self, payment_terms): 
#         if isinstance(payment_terms, str): 
#             payment_terms = json.loads(payment_terms) 
#         self.payment_terms = json.dumps(payment_terms)

#     def get_payment_terms(self): 
#             return json.loads(self.payment_terms)
    


# class PaymentBall(models.Model):
#     PAYMENT_STATUS_CHOICES = [
#         ('Pending', 'Pending'),
#         ('InProgress', 'InProgress'),
#         ('Completed', 'Completed'),
#     ]

#     STATUS_CHOICES = [
#         ('gray', 'Gray'),
#         ('blue', 'Blue'),
#         ('purple', 'Purple'),
#         ('pink', 'Pink'),
#         ('green', 'Green'),
#     ]

#     payment_id = models.AutoField(primary_key=True)
#     job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="payment_balls")
#     project_percentage = models.DecimalField(max_digits=5, decimal_places=2)
#     project_status = models.CharField(max_length=50, default='Pending', choices=PAYMENT_STATUS_CHOICES)
#     notes = models.TextField(blank=True, null=True)
#     status = models.CharField(max_length=6, choices=STATUS_CHOICES, default='gray')
#     invoice_number = models.CharField(max_length=20, blank=True, null=True)  # Generated invoice number
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
    
#     def generate_invoice(self):
#         """Generate a unique invoice number for the payment ball."""
#         if self.status == 'purple' and not self.invoice_number:
#             self.invoice_number = f"INV-{uuid.uuid4().hex[:6].upper()}"
#             self.save()

#     def __str__(self):
#         return f"PaymentBall {self.id} - Status: {self.get_status_display()}"
    

#     def __str__(self): 
#         return f"PaymentBall {self.payment_id} - {self.project_percentage}% for JobCard {self.job_card.job_number}" 
    
#     def set_payment_terms(self, payment_terms): 
#         if isinstance(payment_terms, str): 
#             payment_terms = json.loads(payment_terms) 
#         self.payment_terms = json.dumps(payment_terms) 

#     def get_payment_terms(self): 
#             return json.loads(self.payment_terms)    



































# class JobCard(models.Model):
#     STATUS_CHOICES = [
#         ('Pending', 'Pending'),
#         ('Ongoing', 'Ongoing'),
#         ('Completed', 'Completed'),
#     ]
      
#     job_id = models.AutoField(primary_key=True)
#     rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="job_cards")  # Changed `rfq_id` to `rfq`
#     lpo = models.ForeignKey(LPO, on_delete=models.CASCADE, related_name="job_cards")  # Changed `lpo_id` to `lpo`
#     job_number = models.CharField(max_length=20, unique=True)
#     scope_of_work = models.TextField()
#     delivery_timelines = models.DateField()
#     payment_terms = models.TextField()
#     status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)

#     def __str__(self):
#         return f"JobCard {self.job_number} - {self.rfq.client.client_name}"


# class PaymentBall(models.Model):
#     payment_id = models.AutoField(primary_key=True)
#     job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="payment_balls")
#     project_percentage = models.DecimalField(max_digits=5, decimal_places=2)
#     project_status = models.CharField(max_length=50, default='Pending')
#     notes = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"PaymentBall {self.payment_id} - {self.project_percentage}% for JobCard {self.job_card.job_number}"
    

# class Task(models.Model):
#     STATUS_CHOICES = [
#         ('Pending', 'Pending'),
#         ('Ongoing', 'Ongoing'),
#         ('Completed', 'Completed'),
#     ]
    
#     task_id = models.AutoField(primary_key=True)
#     payment_ball = models.ForeignKey(PaymentBall, on_delete=models.CASCADE, related_name="tasks")
#     task_number = models.CharField(max_length=20, unique=True)
#     task_brief = models.TextField()
#     task_weightage = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
#     assignee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name="assigned_tasks")
#     task_status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)
#     due_date = models.DateField()
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"Task {self.task_number} - {self.task_status}"


# # class SubContracting(models.Model):
#     STATUS_CHOICES = [
#         ('Pending', 'Pending'),
#         ('Ongoing', 'Ongoing'),
#         ('Completed', 'Completed'),
#     ]
    
#     subcontract_id = models.AutoField(primary_key=True)
#     task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="subcontracts")
#     subcontract_number = models.CharField(max_length=20, unique=True)
#     task_brief = models.TextField()
#     task_weightage = models.DecimalField(max_digits=5, decimal_places=2)
#     assignee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name="subcontracted_tasks")
#     task_status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)
#     due_date = models.DateField()
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"SubContract {self.subcontract_number} - {self.task_status}"









# from django.db import models
# from BaseApp.models import Company, Employee

# class Client(models.Model):
#     client_id = models.AutoField(primary_key=True)
#     client_name = models.CharField(max_length=255)
#     contact_info = models.CharField(max_length=255, blank=True, null=True)
#     name = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)  # Link to Company model...change to client company
#     service = models.CharField(
#         max_length=100,
#         choices=Company._meta.get_field('type').choices,
#         blank=True,
#         null=True
#     )
#     about = models.TextField(blank=True, null=True)
#     status = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.client_name


# class RFQ(models.Model):
#     rfq_id = models.AutoField(primary_key=True)
#     client_id = models.ForeignKey(Client, on_delete=models.CASCADE)
#     rfq_date = models.DateTimeField(auto_now_add=True)
#     project_type = models.CharField(max_length=255)
#     scope_of_work = models.TextField()
#     quotation_number = models.CharField(max_length=20, unique=True)
#     quotation_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     remarks = models.TextField(blank=True, null=True)
#     status = models.CharField(max_length=50, default='Pending')

#     def __str__(self):
#         return f"RFQ for {self.client.client_name} - {self.project_type}"


# class LPO(models.Model):
#     lpo_id = models.AutoField(primary_key=True)
#     rfq_id = models.ForeignKey(RFQ, on_delete=models.CASCADE)
#     lpo_number = models.CharField(max_length=20, unique=True)
#     final_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     delivery_timelines = models.DateField()
#     payment_terms = models.TextField()
#     remarks = models.TextField(blank=True, null=True)
#     status = models.CharField(max_length=50, default='Pending')

#     def __str__(self):
#         return f"LPO {self.lpo_number} for RFQ {self.rfq.quotation_number}"


# class JobCard(models.Model):
#     job_id = models.AutoField(primary_key=True)
#     rfq_id = models.ForeignKey(RFQ, on_delete=models.CASCADE)
#     lpo_id = models.ForeignKey(LPO, on_delete=models.CASCADE)
#     job_number = models.CharField(max_length=20, unique=True)
#     scope_of_work = models.TextField()
#     delivery_timelines = models.DateField()
#     payment_terms = models.TextField()
#     status = models.CharField(max_length=50, default='Pending')

#     def __str__(self):
#         return f"JobCard {self.job_number} - {self.rfq.client.client_name}"


# class PaymentBall(models.Model):
#     payment_id = models.AutoField(primary_key=True)
#     job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="payment_balls")
#     project_percentage = models.DecimalField(max_digits=5, decimal_places=2)
#     project_status = models.CharField(max_length=50, default='Pending')
#     notes = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"PaymentBall {self.payment_id} - {self.project_percentage}% for JobCard {self.job_card.job_number}"
