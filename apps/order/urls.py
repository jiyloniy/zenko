from django.urls import path
from apps.order import views

app_name = 'order'

urlpatterns = [
    # Broshkalar
    path('broshka/', views.BrujkaListView.as_view(), name='broshka_list'),
    path('broshka/create/', views.BrujkaCreateView.as_view(), name='broshka_create'),
    path('broshka/<int:pk>/', views.BrujkaDetailView.as_view(), name='broshka_detail'),
    path('broshka/<int:pk>/edit/', views.BrujkaUpdateView.as_view(), name='broshka_edit'),
    path('broshka/<int:pk>/delete/', views.BrujkaDeleteView.as_view(), name='broshka_delete'),
    path('broshka/search/', views.BrujkaSearchAPIView.as_view(), name='broshka_search'),

    # Quyish paneli
    path('quyish/', views.QuyishPanelView.as_view(), name='quyish_panel'),

    # Buyurtmalar
    path('', views.OrderListView.as_view(), name='order_list'),
    path('create/', views.OrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order_edit'),
    path('<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
]
