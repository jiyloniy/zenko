from django.urls import path
from apps.order import views

app_name = 'order'

urlpatterns = [
    # Brujkalar
    path('brujka/', views.BrujkaListView.as_view(), name='brujka_list'),
    path('brujka/create/', views.BrujkaCreateView.as_view(), name='brujka_create'),
    path('brujka/<int:pk>/', views.BrujkaDetailView.as_view(), name='brujka_detail'),
    path('brujka/<int:pk>/edit/', views.BrujkaUpdateView.as_view(), name='brujka_edit'),
    path('brujka/<int:pk>/delete/', views.BrujkaDeleteView.as_view(), name='brujka_delete'),
    path('brujka/search/', views.BrujkaSearchAPIView.as_view(), name='brujka_search'),

    # Buyurtmalar
    path('', views.OrderListView.as_view(), name='order_list'),
    path('create/', views.OrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order_edit'),
    path('<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
]
