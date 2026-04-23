from django.urls import path
from apps.casting import views

app_name = 'casting'

urlpatterns = [
    path('', views.CastingOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.CastingOrderDetailView.as_view(), name='order_detail'),
]
