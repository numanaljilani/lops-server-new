
from rest_framework import viewsets
from .models import Client, RFQ, JobCard, PaymentBall, Task, SubContracting, ExpenseCategory, Expense
from .serializers import ClientSerializer, RFQSerializer, JobCardSerializer, PaymentBallSerializer, TaskSerializer, SubContractingSerializer, ExpenseCategorySerializer, ExpenseSerializer, ExpenseHistorySerializer, AccountsPaymentBallSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend  # Add this import
from .filters import RFQFilter, JobCardFilter  # Import the filter
from django.db.models import Sum 


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
    filterset_fields = ['verification_status', 'project_status']
    print(viewsets)

 

    def get_queryset(self):
        return PaymentBall.objects.select_related(
            'job_card', 'verified_by'
        ).order_by('-verification_date')
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        print(f'urd : {request.data}')
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
                'message': 'Payment ball marked as invoiced'
            })
        return Response({
            'status': 'error',
            'message': 'Cannot mark as invoiced'
        }, status=400)

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


class GlobalSubContractingViewSet(viewsets.ModelViewSet):
    queryset = SubContracting.objects.select_related('task', 'assignee').all()
    serializer_class = SubContractingSerializer

    def get_queryset(self):
        task_id = self.kwargs.get('task_pk')
        if task_id:
            return self.queryset.filter(task_id=task_id)
        return self.queryset   

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()  # Add this line
    serializer_class = ExpenseSerializer
    filterset_fields = ['job_card', 'expense_type', 'status']

    def get_queryset(self):
        queryset = Expense.objects.select_related('job_card', 'category')
        job_card_id = self.request.query_params.get('job_card')
        if job_card_id:
            queryset = queryset.filter(job_card_id=job_card_id)
        return queryset

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

