from rest_framework import serializers
from .models import Client, RFQ, JobCard, PaymentBall, Task, SubContracting, Expense, ExpenseCategory
import json
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder



class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'client_id', 'client_name', 'aob',
            'contact_person', 'contact_number', 'contact_info',
            'company_name', 'service', 'about', 'status',
            'created_at'
        ]


class RFQSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.client_name', read_only=True)  # Add client_name

    class Meta:
        model = RFQ
        fields = [
            'rfq_id', 'client', 'client_name', 'rfq_date', 
            'project_type', 'scope_of_work', 'quotation_number', 
            'quotation_amount', 'remarks', 'status'
        ]





from rest_framework import serializers
import json
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder

class PaymentTermSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)  # Add this for identification
    milestone = serializers.CharField(max_length=100)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description']

class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    job_number = serializers.CharField(source='job_card.job_number', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'expense_id', 'job_card', 'job_number',
            'category', 'category_name', 'expense_type',
            'description', 'amount', 'date', 'status',
            'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        if data.get('amount', 0) <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than 0"})
        return data
    

class ExpenseHistorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    job_number = serializers.CharField(source='job_card.job_number', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'expense_id', 'job_card', 'job_number',
            'category_name', 'expense_type', 'description',
            'amount', 'date', 'status', 'remarks',
            'created_at'
        ]    


class JobCardSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(read_only=True)
    profit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    completion_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    payment_terms = serializers.DictField(
        child=PaymentTermSerializer(),
        required=False,
        write_only=True
    )
    payment_terms_display = serializers.SerializerMethodField()

    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_timesheet_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    gross_profit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    profit_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    expenses = ExpenseSerializer(many=True, read_only=True)

    class Meta:
        model = JobCard
        fields = [
            'job_id', 'rfq', 'job_number', 'client_name',
            'scope_of_work', 'delivery_timelines',
            'payment_terms', 'payment_terms_display', 'status',
            'completion_percentage', 'project_expense', 'profit',
            'created_at', 'color_status',  'total_expenses', 'total_timesheet_cost',
            'gross_profit', 'profit_percentage',
            'expenses'
        ]
        read_only_fields = ['job_id', 'created_at', 'client_name', 'profit', 'completion_percentage']

    def get_payment_terms_display(self, obj):
        """
        Get the payment terms in display format
        """
        if not obj.payment_terms:
            return {}
        
        try:
            terms = json.loads(obj.payment_terms)
            return {
                str(i): {
                    'milestone': term['milestone'],
                    'percentage': term['percentage'],
                    'description': term.get('description', '')
                }
                for i, term in enumerate(terms, 1)
            }
        except (json.JSONDecodeError, TypeError):
            return {}

    def create(self, validated_data):
        payment_terms = validated_data.pop('payment_terms', {})
        instance = super().create(validated_data)
        
        if payment_terms:
            instance.set_payment_terms(payment_terms)
            instance.save(update_fields=['payment_terms'])
        
        return instance

    def update(self, instance, validated_data):
        payment_terms = validated_data.pop('payment_terms', None)
        instance = super().update(instance, validated_data)
        
        if payment_terms is not None:
            instance.set_payment_terms(payment_terms)
            instance.save(update_fields=['payment_terms'])
        
        return instance

    def to_representation(self, instance):
        """
        Override to_representation to handle payment terms display
        """
        representation = super().to_representation(instance)
        representation['payment_terms_display'] = self.get_payment_terms_display(instance)
        return representation

class PaymentBallSerializer(serializers.ModelSerializer):
    payment_terms = serializers.ListField(
        child=PaymentTermSerializer(),
        required=False,
        write_only=True
    )
    payment_terms_display = serializers.SerializerMethodField()

    class Meta:
        model = PaymentBall
        fields = [
            'payment_id', 'job_card', 'project_percentage', 
            'project_status', 'notes', 'color_status', 
            'invoice_number', 'amount', 'payment_terms',
            'payment_terms_display'
        ]
        extra_kwargs = {
            'payment_id': {'read_only': True},
            'invoice_number': {'read_only': True}
        }

    def get_payment_terms_display(self, obj):
        return obj.get_payment_terms()

    def validate(self, data):
        # Validate required fields
        required_fields = ['job_card', 'project_percentage', 'amount']
        for field in required_fields:
            if field not in data:
                raise serializers.ValidationError(f"{field} is required")

        # Validate project_percentage
        if data.get('project_percentage'):
            if not (0 <= data['project_percentage'] <= 100):
                raise serializers.ValidationError(
                    {"project_percentage": "Must be between 0 and 100"}
                )

        # Validate payment_terms if provided
        payment_terms = data.get('payment_terms', [])
        if payment_terms:
            total_percentage = sum(float(term['percentage']) for term in payment_terms)
            if not (99.99 <= total_percentage <= 100.01):
                raise serializers.ValidationError(
                    {"payment_terms": "Total percentage must equal 100%"}
                )

        return data

    def create(self, validated_data):
        payment_terms = validated_data.pop('payment_terms', [])
        instance = super().create(validated_data)
        
        if payment_terms:
            instance.set_payment_terms(payment_terms)
            instance.save()
        
        return instance

    def update(self, instance, validated_data):
        payment_terms = validated_data.pop('payment_terms', None)
        instance = super().update(instance, validated_data)
        
        if payment_terms is not None:
            instance.set_payment_terms(payment_terms)
            instance.save()
        
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop('payment_terms', None)
        representation['payment_terms'] = representation.pop('payment_terms_display', [])
        return representation




class TaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.name', read_only=True)
    payment_ball_details = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'task_id', 'payment_ball', 'payment_ball_details',
            'task_brief', 'weightage', 'status', 'due_date',
            'assignee', 'assignee_name', 'remarks', 
            'completion_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_payment_ball_details(self, obj):
        return {
            'project_percentage': obj.payment_ball.project_percentage,
            'project_status': obj.payment_ball.project_status
        }

    def validate(self, data):
        # Validate weightage
        if data.get('weightage'):
            if not (0 <= data['weightage'] <= 100):
                raise serializers.ValidationError(
                    {"weightage": "Must be between 0 and 100"}
                )

        # Validate completion_percentage
        if data.get('completion_percentage'):
            if not (0 <= data['completion_percentage'] <= 100):
                raise serializers.ValidationError(
                    {"completion_percentage": "Must be between 0 and 100"}
                )

        return data

class SubContractingSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.name', read_only=True)
    task_details = serializers.SerializerMethodField()

    class Meta:
        model = SubContracting
        fields = [
            'subcontract_id', 'task', 'task_details',
            'subcontract_brief', 'weightage', 'status',
            'due_date', 'assignee', 'assignee_name',
            'remarks', 'completion_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_task_details(self, obj):
        return {
            'task_brief': obj.task.task_brief,
            'task_status': obj.task.status
        }

    def validate(self, data):
        # Validate weightage
        if data.get('weightage'):
            if not (0 <= data['weightage'] <= 100):
                raise serializers.ValidationError(
                    {"weightage": "Must be between 0 and 100"}
                )

        # Validate completion_percentage
        if data.get('completion_percentage'):
            if not (0 <= data['completion_percentage'] <= 100):
                raise serializers.ValidationError(
                    {"completion_percentage": "Must be between 0 and 100"}
                )

        return data






        







# from rest_framework import serializers
# from .models import Client, RFQ, Quotation, LPO, JobCard
# class ClientSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Client
#         fields = '__all__'

# class RFQSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = RFQ
#         fields = '__all__'

# class QuotationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Quotation
#         fields = '__all__'

# class LPOSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = LPO
#         fields = '__all__'

# class JobCardSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = JobCard
#         fields = '__all__'


#     def validate_scope_of_work(self, value):
#         if not value:
#             raise serializers.ValidationError("Scope of work cannot be empty.")
#         return value
    
#     def validate(self, data):
#         if 'delivery_timelines' not in data or not data['delivery_timelines']:
#             raise serializers.ValidationError({"delivery_timelines": "Delivery timelines are required."})
#         return data    

#     # def validate_quotation(self, value):
#     #     # Check if the quotation exists
#     #     if not Quotation.objects.filter(id=value.id).exists():
#     #         raise serializers.ValidationError("Quotation does not exist.")
#     #     return value

#     # def validate_lpo(self, value):
#     #     # Check if the LPO exists
#     #     if not LPO.objects.filter(id=value.id).exists():
#     #         raise serializers.ValidationError("LPO does not exist.")
#     #     return value
    
#     # def validate_job_number(self, value):
#     #     # Check if job_number is unique
#     #     if JobCard.objects.filter(job_number=value).exists():
#     #         raise serializers.ValidationError("Job number must be unique.")
#     #     return value

#     # def validate(self, data):
#     #     # Example of any additional validation logic that depends on multiple fields
#     #     if not data['scope_of_work']:
#     #         raise serializers.ValidationError("Scope of work is required.")
#     #     if not data['delivery_timelines']:
#     #         raise serializers.ValidationError("Delivery timelines are required.")
#     #     return data    