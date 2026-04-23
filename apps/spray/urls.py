from django.urls import path
from . import views

app_name = 'spray'

urlpatterns = [
    path('', views.SprayDashboardView.as_view(), name='dashboard'),
    path('orders/', views.SprayOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.SprayOrderDetailView.as_view(), name='order_detail'),
]
