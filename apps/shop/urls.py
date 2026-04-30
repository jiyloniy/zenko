from django.urls import path
from apps.shop import views

app_name = 'shop'

urlpatterns = [
    # Dashboard
    path('', views.ShopDashboardView.as_view(), name='dashboard'),

    # Statistika
    path('stats/', views.ShopStatsView.as_view(), name='stats'),

    # Buyurtmalar
    path('orders/', views.ShopOrderListView.as_view(), name='order_list'),
    path('orders/create/', views.ShopOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.ShopOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/edit/', views.ShopOrderUpdateView.as_view(), name='order_edit'),
    path('orders/<int:pk>/delete/', views.ShopOrderDeleteView.as_view(), name='order_delete'),
    path('orders/<int:pk>/cancel/', views.ShopOrderCancelView.as_view(), name='order_cancel'),

    # Broshkalar
    path('broshkalar/', views.ShopBroshkaListView.as_view(), name='broshka_list'),
    path('broshkalar/<int:pk>/', views.ShopBroshkaDetailView.as_view(), name='broshka_detail'),
]
