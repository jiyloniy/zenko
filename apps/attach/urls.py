from django.urls import path
from . import views

app_name = 'attach'

urlpatterns = [
    path('', views.AttachDashboardView.as_view(), name='dashboard'),
    path('orders/', views.AttachOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.AttachOrderDetailView.as_view(), name='order_detail'),
]
