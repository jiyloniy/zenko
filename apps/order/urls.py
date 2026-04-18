from django.urls import path
from apps.order import views

app_name = 'order'

urlpatterns = [
    # Orders
    path('', views.OrderListView.as_view(), name='order_list'),
    path('create/', views.OrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order_edit'),
    path('<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),

    # Stages
    path('<int:pk>/casting/', views.CastingUpdateView.as_view(), name='casting_edit'),
    path('<int:pk>/montaj/', views.MontajUpdateView.as_view(), name='montaj_edit'),
    path('<int:pk>/hanging/', views.HangingUpdateView.as_view(), name='hanging_edit'),
    path('<int:pk>/stone/', views.StoneSettingUpdateView.as_view(), name='stone_edit'),
    path('<int:pk>/packaging/', views.PackagingUpdateView.as_view(), name='packaging_edit'),
    path('<int:pk>/warehouse/', views.WarehouseUpdateView.as_view(), name='warehouse_edit'),

    # Outsource
    path('<int:pk>/outsource/create/', views.OutsourceCreateView.as_view(), name='outsource_create'),
    path('<int:pk>/outsource/<int:outsource_pk>/edit/', views.OutsourceUpdateView.as_view(), name='outsource_edit'),
    path('<int:pk>/outsource/<int:outsource_pk>/delete/', views.OutsourceDeleteView.as_view(), name='outsource_delete'),

    # Quality Control
    path('<int:pk>/quality/create/', views.QualityCreateView.as_view(), name='quality_create'),
    path('<int:pk>/quality/<int:qc_pk>/edit/', views.QualityUpdateView.as_view(), name='quality_edit'),
    path('<int:pk>/quality/<int:qc_pk>/delete/', views.QualityDeleteView.as_view(), name='quality_delete'),

    # Stage Log CRUD
    path('<int:order_pk>/log/create/', views.OrderStageLogCreateView.as_view(), name='stage_log_create'),
    path('log/<int:pk>/edit/', views.OrderStageLogUpdateView.as_view(), name='stage_log_edit'),
    path('log/<int:pk>/delete/', views.OrderStageLogDeleteView.as_view(), name='stage_log_delete'),
]
