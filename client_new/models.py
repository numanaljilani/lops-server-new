from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json, uuid
from decimal import Decimal
from BaseApp.models import Company, Employee
from timesheet.models import Timesheet
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from .utils import generate_sequential_number

#timesheet employee worlking on whihc prokject related to jobcards - payment of employee to be deducted from profit
#?project_id = 1 - project timesheet, filter timesheet details,  


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
    quotation_number = models.CharField(max_length=20, unique=True) #LETS-QN-YYMM1001 
    quotation_amount = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)

    # New fields
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_rfqs'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Generate quotation number for new records
        if not self.quotation_number and not self.rfq_id:
            self.quotation_number = generate_sequential_number(
                RFQ, "QN", "quotation_number"
            )
        super().save(*args, **kwargs)
    
    def approve(self, approved_by):
        self.is_approved = True
        self.approved_by = approved_by
        self.approval_date = timezone.now()
        self.save()
    

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
    job_number = models.CharField(max_length=20, unique=True) # LTS-JN-YYMM1001
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
    

    ##lpo
    lpo_number = models.CharField(max_length=20, unique=True)

    def save(self, *args, **kwargs):
        # Generate job number for new records
        if not self.job_number and not self.job_id:
            self.job_number = generate_sequential_number(
                JobCard, "JN", "job_number"
            )
            
        # Auto-fill client name
        if self.rfq:
            self.client_name = self.rfq.client.client_name

        # Calculate profit
        if self.rfq and self.project_expense:
            self.profit = self.rfq.quotation_amount - self.project_expense

        # Save the instance
        super().save(*args, **kwargs)

    def update_project_financials(self):
        """Update project financial calculations"""
        # Calculate total approved expenses
        approved_expenses = self.expenses.filter(status='Approved')
        self.total_expenses = sum(expense.amount for expense in approved_expenses)
        
        # Calculate total pending expenses
        pending_expenses = self.expenses.filter(status='Pending')
        total_pending = sum(expense.amount for expense in pending_expenses)
        
        # Calculate total paid and balance
        total_paid = sum(expense.paid_amount for expense in approved_expenses)
        total_balance = sum(expense.balance_amount for expense in approved_expenses)

        # Calculate total timesheet cost
        timesheets = Timesheet.objects.filter(job_card=self)
        self.total_timesheet_cost = sum(
            timesheet.hours_logged * timesheet.hourly_rate 
            for timesheet in timesheets
        )

        # Calculate profit
        if self.rfq:
            total_cost = self.total_expenses + self.total_timesheet_cost
            self.gross_profit = self.rfq.quotation_amount - total_cost
            
            # Calculate profit percentage
            if self.rfq.quotation_amount > 0:
                self.profit_percentage = (self.gross_profit / self.rfq.quotation_amount * 100).quantize(Decimal('0.01'))
            else:
                self.profit_percentage = Decimal('0.00')

        # Save only the financial fields
        self.save(update_fields=[
            'total_expenses', 'total_timesheet_cost', 
            'gross_profit', 'profit_percentage'
        ])





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


    def update_completion_percentage(self):
        """Update job card completion based on payment balls"""
        payment_balls = self.payment_balls.all()
        if not payment_balls.exists():
            return
        
        # Simple average of payment ball percentages
        total_percentage = sum(pb.project_percentage for pb in payment_balls)
        count = payment_balls.count()
        
        if count > 0:
            # Calculate the average completion
            self.completion_percentage = min(Decimal('100'), (total_percentage / count).quantize(Decimal('0.01')))
            
            # Update status based on completion
            if self.completion_percentage >= Decimal('100'):
                self.status = 'Completed'
                self.completion_percentage = Decimal('100')  # Ensure it's exactly 100
            elif self.completion_percentage > Decimal('0'):
                self.status = 'Ongoing'
            else:
                self.status = 'Pending'
            
            # Use update_fields to avoid recursive updates
            self.save(update_fields=['completion_percentage', 'status'])        

        


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
    invoice_number = models.CharField(max_length=20, blank=True, null=True) # LETS-INV-YYMM1001
    Client
    

    def save(self, *args, **kwargs):
    # For new instances (no primary key yet), always set project_percentage to 0
        if not self.pk:
            self.project_percentage = Decimal('0')
            self.project_status = 'Pending'
        
        # Get the current instance from the database if it exists
        if self.pk:
            old_instance = PaymentBall.objects.get(pk=self.pk)
            # Check if verification_status changed to 'verified'
            if self.verification_status == 'verified' and old_instance.verification_status != 'verified':
                self.verification_date = timezone.now()
        else:
            # For new instances, set date if status is verified
            if self.verification_status == 'verified':
                self.verification_date = timezone.now()
        
        super().save(*args, **kwargs)
        
        # If this is a status update to 'Completed', generate invoice
        if self.project_status == 'Completed' and not self.invoice_number:
            self.generate_invoice()

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
            
            # Generate invoice number regardless of color
            if not self.invoice_number:
                from .utils import generate_sequential_number
                self.invoice_number = generate_sequential_number(
                    PaymentBall, "INV", "invoice_number"
                )
                
            self.save(update_fields=['verification_status', 'invoice_number'])
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
        """Generate a sequential invoice number"""
        if not self.invoice_number and self.color_status == 'purple':
            self.invoice_number = generate_sequential_number(
                PaymentBall, "INV", "invoice_number"
            )
            self.save(update_fields=['invoice_number'])
    
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


    def recalculate_completion(self):
        """Force recalculation of project_percentage based on tasks"""
        tasks = self.tasks.all()
        if not tasks.exists():
            return
        
        # Get the first task and call its update method
        first_task = tasks.first()
        if first_task:
            first_task.update_payment_ball_completion()
            
            

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
    # remarks history
    remarks_history = models.JSONField(default=list, blank=True)
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
    

    def save(self, *args, **kwargs):
        # Track remarks history if this is an update
        if self.pk:
            old_task = Task.objects.get(pk=self.pk)
            
            # If remarks have changed, save to history
            if old_task.remarks != self.remarks and old_task.remarks:
                if not self.remarks_history:
                    self.remarks_history = []
                
                self.remarks_history.append({
                    'remarks': old_task.remarks,
                    'timestamp': timezone.now().isoformat(),
                    'status': old_task.status,
                    'completion_percentage': float(old_task.completion_percentage)
                })
            
            # Auto-update status based on completion percentage
            if float(self.completion_percentage) == 0:
                self.status = 'Pending'
            elif float(self.completion_percentage) < 100:
                self.status = 'InProgress'
            elif float(self.completion_percentage) == 100:
                self.status = 'Completed'
        
        # Call the original save method
        super().save(*args, **kwargs)
        
        # Update parent payment ball after saving
        self.update_payment_ball_completion()
    
    def update_payment_ball_completion(self):
        """Update the parent payment ball's completion percentage based on all tasks"""
        payment_ball = self.payment_ball
        tasks = payment_ball.tasks.all()
        
        if not tasks.exists():
            return
        
        # Calculate the weighted completion percentage
        total_weightage = sum(task.weightage for task in tasks)
        
        if total_weightage == 0:
            payment_ball.project_percentage = Decimal('0')
            payment_ball.save(update_fields=['project_percentage'])
            return
            
        # Calculate the weighted completion
        weighted_completion = Decimal('0')
        for task in tasks:
            task_contribution = (task.weightage / total_weightage) * (task.completion_percentage / Decimal('100'))
            weighted_completion += task_contribution * Decimal('100')
        
        # Update the payment ball's project_percentage
        payment_ball.project_percentage = weighted_completion.quantize(Decimal('0.01'))
        
        # Update status based on completion
        if payment_ball.project_percentage == 0:
            payment_ball.project_status = 'Pending'
        elif payment_ball.project_percentage >= 100:
            payment_ball.project_status = 'Completed'
            payment_ball.project_percentage = Decimal('100')  # Cap at 100
        else:
            payment_ball.project_status = 'InProgress'
        
        # Save the payment ball
        payment_ball.save(update_fields=['project_percentage', 'project_status'])
        
        # Update the JobCard completion percentage
        if hasattr(payment_ball, 'job_card'):
            payment_ball.job_card.update_completion_percentage()
    
    

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
class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


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
    
    PAYMENT_MODE_CHOICES = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Credit Card', 'Credit Card'),
        ('Other', 'Other'),
    ]

    expense_id = models.AutoField(primary_key=True)
    job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='expenses')
    # Auto-populate LPO number from JobCard
    lpo_number = models.CharField(max_length=20, blank=True, null=True, editable=False)
    # Link to supplier
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='expenses')
    
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    description = models.TextField()
    
    # Financial values
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Net amount without tax")
    vat_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, 
                                        validators=[MinValueValidator(0), MaxValueValidator(100)])
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False, 
                                help_text="Total amount including VAT")
    
    # Payment details
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='Cash')
    payment_date = models.DateField(null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    due_date = models.DateField(null=True, blank=True)
    
    # Status fields
    date = models.DateField()
    status = models.CharField(max_length=20, choices=EXPENSE_STATUS_CHOICES, default='Pending')
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Expense {self.expense_id} - {self.job_card.job_number} - {self.amount}"

    def save(self, *args, **kwargs):
        # Auto-populate LPO number from JobCard
        if self.job_card and not self.lpo_number:
            self.lpo_number = self.job_card.lpo_number
            
        # Calculate VAT and total amount
        self.vat_amount = (self.net_amount * self.vat_percentage / 100).quantize(Decimal('0.01'))
        self.amount = self.net_amount + self.vat_amount
        
        # Calculate balance
        self.balance_amount = self.amount - self.paid_amount
        
        super().save(*args, **kwargs)
        self.job_card.update_project_financials()   

### subcontractor model like client #### to be completed
### percentage - 















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
