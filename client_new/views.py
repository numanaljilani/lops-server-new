
from rest_framework import viewsets
from .models import Client, RFQ, JobCard, PaymentBall, Task, SubContracting, ExpenseCategory, Expense, Supplier
from .serializers import ClientSerializer, RFQSerializer, JobCardSerializer, PaymentBallSerializer, TaskSerializer, SubContractingSerializer, ExpenseCategorySerializer, ExpenseSerializer, ExpenseHistorySerializer, AccountsPaymentBallSerializer, SupplierSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend  # Add this import

from .filters import RFQFilter, JobCardFilter,  ExpenseFilter # Import the filter
from django.db.models import Sum, Count 
from django.utils import timezone
from rest_framework.decorators import action
from BaseApp.serializers import EmployeeSerializer
from BaseApp.models import Employee




class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.order_by('-created_at').all()
    serializer_class = ClientSerializer

class RFQViewSet(viewsets.ModelViewSet):
    queryset = RFQ.objects.order_by('-rfq_date').all()
    serializer_class = RFQSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = RFQFilter

    def get_queryset(self):
        client_id = self.kwargs['client_pk']
        return RFQ.objects.filter(client__client_id=client_id)
    
    
class GlobalRFQViewSet(viewsets.ModelViewSet):
    queryset = RFQ.objects.all()
    serializer_class = RFQSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = RFQFilter

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        rfq = self.get_object()
        
        # Get the employee (assuming user has employee relationship)
        # For testing, you might need to specify an employee ID
        employee_id = request.data.get('employee_id')  # Optional for testing
        if employee_id:
            approved_by = Employee.objects.get(id=employee_id)
        else:
            # In production with proper authentication:
            approved_by = request.user.employee
            approved_by = None  # For now
        
        rfq.approve(approved_by)
        
        serializer = self.get_serializer(rfq)
        return Response({
            'status': 'success',
            'message': 'RFQ approved successfully',
            'rfq': serializer.data
        })


from rest_framework import viewsets
from .models import JobCard, PaymentBall
from .serializers import JobCardSerializer, PaymentBallSerializer

class GlobalJobCardViewSet(viewsets.ModelViewSet):
    queryset = JobCard.objects.order_by('-created_at').all().prefetch_related('payment_balls') 
    serializer_class = JobCardSerializer

    def get_serializer(self, *args, **kwargs):
        """
        Handle both single and multiple objects.
        """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)
    
    filter_backends = [DjangoFilterBackend]
    filterset_class = JobCardFilter

    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        job_card = self.get_object()
        
        # Get all payment balls for this job card
        payment_balls = job_card.payment_balls.all()
        
        # Collect all employee IDs
        employee_ids = set()
        for payment_ball in payment_balls:
            # Get tasks for this payment ball
            tasks = payment_ball.tasks.all()
            
            # Get assignees from tasks
            for task in tasks:
                if task.assignee:
                    employee_ids.add(task.assignee.id)
                
                # Also get assignees from subcontracts
                for subcontract in task.subcontracts.all():
                    if subcontract.assignee:
                        employee_ids.add(subcontract.assignee.id)
        
        # Get employee objects
        employees = Employee.objects.filter(id__in=employee_ids)
        
        # Serialize and return - pass the request context
        serializer = EmployeeSerializer(employees, many=True, context={'request': request})
        return Response(serializer.data)
    

    @action(detail=True, methods=['get'])
    def expenses(self, request, pk=None):
        job_card = self.get_object()
        expenses = job_card.expenses.all()
        
        # Optional: Filter by status
        status = request.query_params.get('status')
        if status:
            expenses = expenses.filter(status=status)
        
        # Optional: Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)
        
        # Calculate totals
        total = expenses.aggregate(total=Sum('amount'))['total'] or 0
        approved_total = expenses.filter(status='Approved').aggregate(total=Sum('amount'))['total'] or 0
        
        # Serialize expenses
        serializer = ExpenseSerializer(expenses, many=True)
        
        return Response({
            'expenses': serializer.data,
            'summary': {
                'total_expenses': total,
                'approved_expenses': approved_total,
                'count': expenses.count()
            }
        })
    
    

class PaymentBallViewSet(viewsets.ModelViewSet):
    queryset = PaymentBall.objects.all().select_related('job_card')
    serializer_class = PaymentBallSerializer

    def get_queryset(self):
        queryset = PaymentBall.objects.all().select_related('job_card')
        job_card_id = self.request.query_params.get('job_card', None)
        # print(job_card_id)
        
        if job_card_id:
            queryset = queryset.filter(job_card_id=job_card_id)
            # print(queryset)
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_job_card(self, request):
        job_card_id = request.query_params.get('job_card')
        if not job_card_id:
            return Response(
                {"error": "job_card parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_balls = self.get_queryset().filter(job_card_id=job_card_id)
        serializer = self.get_serializer(payment_balls, many=True)
        return Response(serializer.data)


# client_new/views.py

class AccountsPaymentBallViewSet(viewsets.ModelViewSet):
    serializer_class = AccountsPaymentBallSerializer
    queryset = PaymentBall.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['verification_status', 'project_status', 'project_percentage']

    def get_queryset(self):
        return PaymentBall.objects.select_related(
            
        ).all()

    def get_queryset(self):
        return PaymentBall.objects.select_related(
            'job_card', 
            'job_card__rfq', 
            'job_card__rfq__client',
            'verified_by'
        ).order_by('-verification_date')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)  # Debugging line
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_update(serializer)
        return Response(serializer.data)    



    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        payment_ball = self.get_object()
        verified_by = request.user.employee  # Assuming user-employee relationship
        
        if payment_ball.verify_completion(verified_by):
            return Response({
                'status': 'success',
                'message': 'Payment ball verified successfully'
            })
        return Response({
            'status': 'error',
            'message': 'Cannot verify payment ball'
        }, status=400)

    @action(detail=True, methods=['post'])
    def mark_invoiced(self, request, pk=None):
        payment_ball = self.get_object()
        
        if payment_ball.mark_as_invoiced():
            return Response({
                'status': 'success',
                'message': 'Payment ball marked as invoiced',
                'invoice_number': payment_ball.invoice_number
            })
        return Response({
            'status': 'error',
            'message': 'Cannot mark as invoiced. Payment ball must be verified first.'
        }, status=400)
    
    @action(detail=True, methods=['post'])
    def generate_invoice(self, request, pk=None):
        """Generate invoice number without changing status"""
        payment_ball = self.get_object()
        invoice_number = payment_ball.generate_invoice_number()
        
        return Response({
            'status': 'success',
            'message': 'Invoice number generated',
            'invoice_number': invoice_number
        })

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        payment_ball = self.get_object()
        if payment_ball.mark_as_paid():
            return Response({
                'status': 'success',
                'message': 'Payment ball marked as paid'
            })
        return Response({
            'status': 'error',
            'message': 'Cannot mark as paid'
        }, status=400)

    @action(detail=False)
    def pending_verification(self, request):
        queryset = self.get_queryset().filter(
            project_status='Completed',
            verification_status='unverified'
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False)
    def pending_payment(self, request):
        queryset = self.get_queryset().filter(
            verification_status='invoiced'
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False)
    def payment_summary(self, request):
        summary = {
            'unverified': self.get_queryset().filter(verification_status='unverified').count(),
            'verified': self.get_queryset().filter(verification_status='verified').count(),
            'invoiced': self.get_queryset().filter(verification_status='invoiced').count(),
            'paid': self.get_queryset().filter(verification_status='paid').count(),
            'total_amount': {
                'pending': self.get_queryset().filter(verification_status='unverified').aggregate(
                    total=Sum('amount')
                )['total'] or 0,
                'received': self.get_queryset().filter(verification_status='paid').aggregate(
                    total=Sum('amount')
                )['total'] or 0
            }
        }
        return Response(summary)
    

    @action(detail=False)
    def completed(self, request):
        """Get all payment balls that are 100% complete"""
        queryset = self.get_queryset().filter(project_percentage=100)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('payment_ball', 'assignee').all()
    serializer_class = TaskSerializer

    def get_queryset(self):
        queryset = Task.objects.all().select_related('payment_ball')
        payment_ball = self.request.query_params.get('payment_ball', None)
        # print(job_card_id)
        
        if payment_ball:
            queryset = queryset.filter(payment_ball=payment_ball)
            print(queryset)
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_payment_ball(self, request):
        payment_ball = request.query_params.get('payment_ball')
        if not payment_ball:
            return Response(
                {"error": "payment_ball parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_balls = self.get_queryset().filter(payment_ball=payment_ball)
        serializer = self.get_serializer(payment_balls, many=True)
        return Response(serializer.data)


class SubContractingViewSet(viewsets.ModelViewSet):
    queryset = SubContracting.objects.select_related('task', 'assignee').all()
    serializer_class = SubContractingSerializer

    def get_queryset(self):
        task_id = self.kwargs.get('task_pk')
        if task_id:
            return self.queryset.filter(task_id=task_id)
        return self.queryset

class GlobalTaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('payment_ball', 'assignee').all()
    serializer_class = TaskSerializer
    

    def get_queryset(self):
        queryset = Task.objects.all().select_related('payment_ball')
        payment_ball = self.request.query_params.get('payment_ball', None)
        # print(job_card_id)
        
        if payment_ball:
            queryset = queryset.filter(payment_ball=payment_ball)
            print(queryset)
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_payment_ball(self, request):
        payment_ball = request.query_params.get('payment_ball')
        if not payment_ball:
            return Response(
                {"error": "payment_ball parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_balls = self.get_queryset().filter(payment_ball=payment_ball)
        serializer = self.get_serializer(payment_balls, many=True)
        return Response(serializer.data)
    

    @action(detail=True, methods=['get'])
    def remarks_history(self, request, pk=None):
        task = self.get_object()
        history = task.remarks_history
        
        # Add current remarks if they exist
        if task.remarks:
            current = {
                'remarks': task.remarks,
                'timestamp': task.updated_at.isoformat(),
                'status': task.status,
                'completion_percentage': float(task.completion_percentage),
                'current': True
            }
            history = [current] + (history or [])
            
        return Response(history)
    
    @action(detail=True, methods=['post'])
    def update_parent(self, request, pk=None):
        """Manually trigger update of the parent payment ball"""
        task = self.get_object()
        task.update_payment_ball_completion()
        return Response({
            'status': 'success',
            'payment_ball_percentage': float(task.payment_ball.project_percentage),
            'payment_ball_status': task.payment_ball.project_status
        })
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Manually recalculate the completion percentage"""
        task = self.get_object()  # This is correctly getting a Task object
        # Update parent payment ball
        task.update_payment_ball_completion()
        return Response({
            'status': 'success',
            'task_completion': float(task.completion_percentage),
            'payment_ball_percentage': float(task.payment_ball.project_percentage),
            'payment_ball_status': task.payment_ball.project_status
        })




class GlobalSubContractingViewSet(viewsets.ModelViewSet):
    queryset = SubContracting.objects.select_related('task', 'assignee').all()
    serializer_class = SubContractingSerializer

    def get_queryset(self):
        task_id = self.kwargs.get('task_pk')
        if task_id:
            return self.queryset.filter(task_id=task_id)
        return self.queryset   



class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    filterset_class = ExpenseFilter
    
    def get_queryset(self):
        queryset = Expense.objects.select_related(
            'job_card', 'category', 'supplier'
        ).order_by('-date')
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_job_card(self, request):
        """Get expenses for a specific job card with summary"""
        job_card_id = request.query_params.get('job_card')
        if not job_card_id:
            return Response(
                {"error": "job_card parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        expenses = self.filter_queryset(
            self.get_queryset().filter(job_card_id=job_card_id)
        )
        
        # Calculate totals
        total = expenses.aggregate(total=Sum('amount'))['total'] or 0
        total_net = expenses.aggregate(total=Sum('net_amount'))['total'] or 0
        total_vat = expenses.aggregate(total=Sum('vat_amount'))['total'] or 0
        total_paid = expenses.aggregate(total=Sum('paid_amount'))['total'] or 0
        total_balance = expenses.aggregate(total=Sum('balance_amount'))['total'] or 0
        
        # Status breakdown
        status_breakdown = expenses.values('status').annotate(
            count=Count('expense_id'),
            total=Sum('amount')
        )
        
        # Type breakdown
        type_breakdown = expenses.values('expense_type').annotate(
            count=Count('expense_id'),
            total=Sum('amount')
        )
        
        # Supplier breakdown
        supplier_breakdown = expenses.values(
            'supplier', 'supplier__name'
        ).annotate(
            count=Count('expense_id'),
            total=Sum('amount')
        )
        
        # Paginate the expenses for the list view
        page = self.paginate_queryset(expenses)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['summary'] = {
                'total_expenses': float(total),
                'total_net': float(total_net),
                'total_vat': float(total_vat),
                'total_paid': float(total_paid),
                'total_balance': float(total_balance),
                'count': expenses.count(),
                'status_breakdown': status_breakdown,
                'type_breakdown': type_breakdown,
                'supplier_breakdown': supplier_breakdown
            }
            return response
            
        serializer = self.get_serializer(expenses, many=True)
        return Response({
            'expenses': serializer.data,
            'summary': {
                'total_expenses': float(total),
                'total_net': float(total_net),
                'total_vat': float(total_vat),
                'total_paid': float(total_paid),
                'total_balance': float(total_balance),
                'count': expenses.count(),
                'status_breakdown': status_breakdown,
                'type_breakdown': type_breakdown,
                'supplier_breakdown': supplier_breakdown
            }
        })
        
    @action(detail=False, methods=['get'])
    def unpaid(self, request):
        """Get all expenses with outstanding balance"""
        queryset = self.get_queryset().filter(balance_amount__gt=0)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()  # Add this line
    serializer_class = ExpenseCategorySerializer

    def perform_update(self, serializer):
        expense = serializer.save()
        expense.job_card.update_project_financials()

class ExpenseHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseHistorySerializer
    filterset_fields = ['job_card', 'expense_type', 'status']

    def get_queryset(self):
        queryset = Expense.objects.all().select_related('job_card', 'category')
        
        # Filter by job_card if provided
        job_card_id = self.request.query_params.get('job_card')
        if job_card_id:
            queryset = queryset.filter(job_card_id=job_card_id)
            
        return queryset

    @action(detail=False, methods=['get'])
    def job_card_expenses(self, request):
        """Get all expenses for a specific job card"""
        job_card_id = request.query_params.get('job_card')
        if not job_card_id:
            return Response({"error": "job_card parameter is required"}, status=400)

        expenses = self.get_queryset().filter(job_card_id=job_card_id)
        serializer = self.get_serializer(expenses, many=True)
        
        # Calculate totals
        total_approved = sum(exp.amount for exp in expenses if exp.status == 'Approved')
        total_pending = sum(exp.amount for exp in expenses if exp.status == 'Pending')
        
        return Response({
            'expenses': serializer.data,
            'summary': {
                'total_approved': total_approved,
                'total_pending': total_pending,
                'total_expenses': total_approved + total_pending
            }
        })      


    @action(detail=False, methods=['get'])
    def job_card_summary(self, request):
        """Get expense summary for a specific job card"""
        job_card_id = request.query_params.get('job_card')
        if not job_card_id:
            return Response({"error": "job_card parameter is required"}, status=400)

        expenses = self.get_queryset().filter(job_card_id=job_card_id)
        
        # Group by supplier
        supplier_totals = {}
        for exp in expenses:
            supplier_id = exp.supplier_id
            supplier_name = exp.supplier.name
            
            if supplier_id not in supplier_totals:
                supplier_totals[supplier_id] = {
                    'supplier_id': supplier_id,
                    'supplier_name': supplier_name,
                    'net_total': 0,
                    'vat_total': 0,
                    'total': 0,
                    'paid': 0,
                    'balance': 0,
                    'count': 0
                }
            
            supplier_totals[supplier_id]['net_total'] += float(exp.net_amount)
            supplier_totals[supplier_id]['vat_total'] += float(exp.vat_amount)
            supplier_totals[supplier_id]['total'] += float(exp.amount)
            supplier_totals[supplier_id]['paid'] += float(exp.paid_amount)
            supplier_totals[supplier_id]['balance'] += float(exp.balance_amount)
            supplier_totals[supplier_id]['count'] += 1
        
        # Overall totals
        overall = {
            'net_total': sum(float(exp.net_amount) for exp in expenses),
            'vat_total': sum(float(exp.vat_amount) for exp in expenses),
            'total': sum(float(exp.amount) for exp in expenses),
            'paid': sum(float(exp.paid_amount) for exp in expenses),
            'balance': sum(float(exp.balance_amount) for exp in expenses),
            'count': expenses.count()
        }
        
        return Response({
            'supplier_breakdown': list(supplier_totals.values()),
            'overall': overall
        })  


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filterset_fields = ['name', 'status']











# from django.shortcuts import render

# # Create your views here.
# from rest_framework import status, viewsets
# from rest_framework.response import Response
# from rest_framework.decorators import action
# from .models import Client, RFQ, Quotation, LPO,  JobCard
# from .serializers import ClientSerializer, RFQSerializer, QuotationSerializer, LPOSerializer, JobCardSerializer

# class ClientViewSet(viewsets.ModelViewSet):
#     queryset = Client.objects.all()
#     serializer_class = ClientSerializer

# class RFQViewSet(viewsets.ModelViewSet):
#     queryset = RFQ.objects.all()
#     serializer_class = RFQSerializer

#     def get_queryset(self):
#         client_id = self.kwargs['client_pk']
#         return RFQ.objects.filter(client__client_id=client_id)

# class QuotationViewSet(viewsets.ModelViewSet):
#     queryset = Quotation.objects.all()
#     serializer_class = QuotationSerializer

#     def get_queryset(self):
#         rfq_id = self.kwargs['rfq_pk']
#         return Quotation.objects.filter(rfq__rfq_id=rfq_id)

# class LPOViewSet(viewsets.ModelViewSet):
#     queryset = LPO.objects.all()
#     serializer_class = LPOSerializer

#     def get_queryset(self):
#         quotation_id = self.kwargs['quotation_pk']
#         return LPO.objects.filter(quotation__quotation_id=quotation_id)

# class RFQViewSet(viewsets.ModelViewSet):
#     serializer_class = RFQSerializer

#     def get_queryset(self):
#         client_id = self.kwargs['client_pk']
#         return RFQ.objects.filter(client__client_id=client_id)

# class QuotationViewSet(viewsets.ModelViewSet):
#     serializer_class = QuotationSerializer

#     def get_queryset(self):
#         rfq_id = self.kwargs['rfq_pk']
#         return Quotation.objects.filter(rfq__rfq_id=rfq_id)

# class LPOViewSet(viewsets.ModelViewSet):
#     serializer_class = LPOSerializer

#     def get_queryset(self):
#         quotation_id = self.kwargs['quotation_pk']
#         return LPO.objects.filter(quotation__quotation_id=quotation_id)

# class JobCardViewSet(viewsets.ModelViewSet):
#     serializer_class = JobCardSerializer

#     def get_queryset(self):
#         lpo_id = self.kwargs['lpo_pk']
#         return JobCard.objects.filter(lpo__lpo_id=lpo_id)








# class JobCardViewSet(viewsets.ModelViewSet):
#     queryset = JobCard.objects.all()
#     serializer_class = JobCardSerializer

#     @action(detail=False, methods=['post'], url_path='create-jobcard')
#     def create_job_card(self, request):
#         quotation_id = request.data.get('quotation_id')
#         lpo_id = request.data.get('lpo_id')
#         job_number = request.data.get('job_number')
#         scope_of_work = request.data.get('scope_of_work')
#         delivery_timelines = request.data.get('delivery_timelines')
#         payment_terms = request.data.get('payment_terms')

#         try:
#             # Retrieve the Quotation and LPO
#             quotation = Quotation.objects.get(pk=quotation_id)
#             lpo = LPO.objects.get(pk=lpo_id)

#             # Create JobCard
#             job_card = JobCard.objects.create(
#                 quotation=quotation,
#                 lpo=lpo,
#                 job_number=job_number,
#                 scope_of_work=scope_of_work,
#                 delivery_timelines=delivery_timelines,
#                 payment_terms=payment_terms,
#                 status='Pending'
#             )

#             # Serialize and return the created JobCard
#             serializer = JobCardSerializer(job_card)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)

#         except Quotation.DoesNotExist:
#             return Response({"error": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)
#         except LPO.DoesNotExist:
#             return Response({"error": "LPO not found."}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

