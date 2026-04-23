from django.urls import path
from . import views

app_name = 'stone'

urlpatterns = [
    path('', views.StoneDashboardView.as_view(), name='dashboard'),
    path('orders/', views.StoneOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.StoneOrderDetailView.as_view(), name='order_detail'),
]
