from django.urls import path
from . import views

app_name = 'casting'

urlpatterns = [
    path('', views.CastingDashboardView.as_view(), name='dashboard'),
    path('orders/', views.CastingOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.CastingOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/update/', views.CastingStageUpdateView.as_view(), name='stage_update'),
    path('orders/<int:pk>/transfer/', views.CastingTransferView.as_view(), name='transfer'),
]
