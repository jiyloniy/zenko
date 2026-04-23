from django.urls import path
from . import views

app_name = 'assembly'

urlpatterns = [
    path('', views.AssemblyDashboardView.as_view(), name='dashboard'),
    path('orders/', views.AssemblyOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.AssemblyOrderDetailView.as_view(), name='order_detail'),
]
