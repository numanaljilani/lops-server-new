from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    ClientViewSet,
    PaymentBallViewSet, GlobalRFQViewSet, 
    GlobalJobCardViewSet,  
    GlobalTaskViewSet, GlobalSubContractingViewSet, ExpenseCategoryViewSet, ExpenseViewSet, AccountsPaymentBallViewSet, SupplierViewSet
)

# Global router for independent access
global_router = routers.DefaultRouter()
global_router.register(r'clients', ClientViewSet)
global_router.register(r'rfqs', GlobalRFQViewSet, basename='rfqs')
global_router.register(r'jobcards', GlobalJobCardViewSet, basename='jobcards')
global_router.register(r'paymentballs', PaymentBallViewSet, basename='paymentballs')
global_router.register(r'tasks', GlobalTaskViewSet, basename='tasks')
global_router.register(r'subcontracts', GlobalSubContractingViewSet, basename='subcontracts')
global_router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expense')
global_router.register(r'expenses', ExpenseViewSet, basename='expense-category')

global_router.register(r'suppliers', SupplierViewSet, basename='supplier')

global_router.register(
    r'accounts/payment-balls',
    AccountsPaymentBallViewSet,
    basename='accounts-paymentballs'
)



# Nested routers
# router = routers.DefaultRouter()
# router.register(r'clients', ClientViewSet)

# clients_router = routers.NestedDefaultRouter(router, r'clients', lookup='client')
# clients_router.register(r'rfqs', RFQViewSet, basename='client-rfqs')

# # Remove the LPO-related routers as you've removed the LPO model
# # rfqs_router = routers.NestedDefaultRouter(clients_router, r'rfqs', lookup='rfq')
# # rfqs_router.register(r'lpos', JobCardViewSet, basename='rfq-lpos') 

# # Directly nest JobCards under RFQs 
# rfqs_router = routers.NestedDefaultRouter(clients_router, r'rfqs', lookup='rfq')
# rfqs_router.register(r'jobcards', JobCardViewSet, basename='rfq-jobcards') 

# jobcards_router = routers.NestedDefaultRouter(rfqs_router, r'jobcards', lookup='job_card')
# jobcards_router.register(r'paymentballs', PaymentBallViewSet, basename='jobcard-paymentballs')

# tasks_router = routers.NestedDefaultRouter(jobcards_router, r'paymentballs', lookup='payment_ball')
# tasks_router.register(r'tasks', TaskViewSet, basename='paymentball-tasks')

# subcontracts_router = routers.NestedDefaultRouter(tasks_router, r'tasks', lookup='task')
# subcontracts_router.register(r'subcontracts', SubContractingViewSet, basename='task-subcontracts')

# URL patterns
urlpatterns = [
    path('client_new/', include(global_router.urls)),  # Independent global access
    # path('client_new/', include(router.urls)),
    # path('client_new/', include(clients_router.urls)),
    # path('client_new/', include(rfqs_router.urls)),
    # # path('client_new/', include(lpos_router.urls)),  # Removed LPO-related URL
    # path('client_new/', include(jobcards_router.urls)),
    # path('client_new/', include(tasks_router.urls)),
    # path('client_new/', include(subcontracts_router.urls)),
]