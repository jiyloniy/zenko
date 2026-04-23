from django.urls import path
from apps.casting import views

app_name = 'casting'

urlpatterns = [
    # Orders
    path('', views.CastingOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.CastingOrderDetailView.as_view(), name='order_detail'),

    # Stanoklar
    path('stanoklar/', views.StanokListView.as_view(), name='stanok_list'),
    path('stanoklar/create/', views.StanokCreateView.as_view(), name='stanok_create'),
    path('stanoklar/<int:pk>/edit/', views.StanokUpdateView.as_view(), name='stanok_edit'),
    path('stanoklar/<int:pk>/delete/', views.StanokDeleteView.as_view(), name='stanok_delete'),
]
