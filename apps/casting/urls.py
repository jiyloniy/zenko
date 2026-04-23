from django.urls import path
from . import views

app_name = 'casting'

urlpatterns = [
    path('', views.CastingDashboardView.as_view(), name='dashboard'),
    path('orders/', views.CastingOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.CastingOrderDetailView.as_view(), name='order_detail'),
    # Stanok CRUD
    path('stanoklar/', views.StanokListView.as_view(), name='stanok_list'),
    path('stanoklar/create/', views.StanokCreateView.as_view(), name='stanok_create'),
    path('stanoklar/<int:pk>/edit/', views.StanokUpdateView.as_view(), name='stanok_edit'),
    path('stanoklar/<int:pk>/delete/', views.StanokDeleteView.as_view(), name='stanok_delete'),
    # Stanok loglari
    path('stanok-logs/', views.StanokLogListView.as_view(), name='stanok_log_list'),
]
