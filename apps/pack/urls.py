from django.urls import path
from . import views

app_name = 'pack'

urlpatterns = [
    path('', views.PackDashboardView.as_view(), name='dashboard'),
    path('orders/', views.PackOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.PackOrderDetailView.as_view(), name='order_detail'),
]
