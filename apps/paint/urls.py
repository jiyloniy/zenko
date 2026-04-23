from django.urls import path
from . import views

app_name = 'paint'

urlpatterns = [
    path('', views.PaintDashboardView.as_view(), name='dashboard'),
    path('orders/', views.PaintOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.PaintOrderDetailView.as_view(), name='order_detail'),
]
