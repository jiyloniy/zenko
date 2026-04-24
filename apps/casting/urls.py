from django.urls import path
from apps.casting import views

app_name = 'casting'

urlpatterns = [
    # Orders
    path('', views.CastingOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.CastingOrderDetailView.as_view(), name='order_detail'),
    path('stats/', views.CastingStatsView.as_view(), name='stats'),
    path('orders/<int:pk>/log/', views.OrderLogView.as_view(), name='order_log'),
    path('orders/<int:pk>/hom/add/', views.HomLogCreateView.as_view(), name='hom_log_add'),
    path('orders/<int:pk>/hom/<int:log_pk>/delete/', views.HomLogDeleteView.as_view(), name='hom_log_delete'),
    path('orders/<int:pk>/tayor/add/', views.TayorLogCreateView.as_view(), name='tayor_log_add'),
    path('orders/<int:pk>/tayor/<int:log_pk>/delete/', views.TayorLogDeleteView.as_view(), name='tayor_log_delete'),

    # Stanoklar
    path('stanoklar/', views.StanokListView.as_view(), name='stanok_list'),
    path('stanoklar/create/', views.StanokCreateView.as_view(), name='stanok_create'),
    path('stanoklar/<int:pk>/edit/', views.StanokUpdateView.as_view(), name='stanok_edit'),
    path('stanoklar/<int:pk>/delete/', views.StanokDeleteView.as_view(), name='stanok_delete'),
]
