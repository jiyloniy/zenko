from django.urls import path
from apps.casting import views

app_name = 'casting'

urlpatterns = [
    # Orders (new + in_process)
    path('', views.CastingOrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.CastingOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/set-status/', views.OrderSetStatusView.as_view(), name='order_set_status'),
    path('stats/', views.CastingStatsView.as_view(), name='stats'),
    path('orders/<int:pk>/log/', views.OrderLogView.as_view(), name='order_log'),
    path('orders/<int:pk>/hom/add/', views.HomLogCreateView.as_view(), name='hom_log_add'),
    path('orders/<int:pk>/hom/<int:log_pk>/delete/', views.HomLogDeleteView.as_view(), name='hom_log_delete'),
    path('orders/<int:pk>/tayor/add/', views.TayorLogCreateView.as_view(), name='tayor_log_add'),
    path('orders/<int:pk>/tayor/<int:log_pk>/delete/', views.TayorLogDeleteView.as_view(), name='tayor_log_delete'),
    
    # Quyish rasxodlari
    path('quyish-rasxod/', views.QuyishRasxodListView.as_view(), name='quyish_rasxod_list'),
    path('quyish-rasxod/create/', views.QuyishRasxodCreateView.as_view(), name='quyish_rasxod_create'),
    path('quyish-rasxod/<int:pk>/edit/', views.QuyishRasxodUpdateView.as_view(), name='quyish_rasxod_edit'),
    path('quyish-rasxod/<int:pk>/delete/', views.QuyishRasxodDeleteView.as_view(), name='quyish_rasxod_delete'),

    # Stanoklar
    path('stanoklar/', views.StanokListView.as_view(), name='stanok_list'),
    path('stanoklar/create/', views.StanokCreateView.as_view(), name='stanok_create'),
    path('stanoklar/<int:pk>/edit/', views.StanokUpdateView.as_view(), name='stanok_edit'),
    path('stanoklar/<int:pk>/delete/', views.StanokDeleteView.as_view(), name='stanok_delete'),

    # Rasxod
    path('rasxod/', views.RasxodListView.as_view(), name='rasxod_list'),
    path('rasxod/add/', views.RasxodCreateView.as_view(), name='rasxod_add'),
    path('rasxod/<int:pk>/delete/', views.RasxodDeleteView.as_view(), name='rasxod_delete'),

    # Zamak
    path('zamaklar/', views.ZamakListView.as_view(), name='zamak_list'),
    path('zamaklar/add/', views.ZamakCreateView.as_view(), name='zamak_add'),
    path('zamaklar/<int:pk>/delete/', views.ZamakDeleteView.as_view(), name='zamak_delete'),

    # Order manage (casting manager CRUD)
    path('manage/', views.OrderManageListView.as_view(), name='order_manage_list'),
    path('manage/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('manage/<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order_edit'),
    path('manage/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    path('manage/<int:pk>/set-status/', views.OrderSetStatusView2.as_view(), name='order_set_status2'),

    # Brujkalar
    path('brujkalar/', views.BrujkaListView.as_view(), name='brujka_list'),
    path('brujkalar/<int:pk>/', views.BrujkaDetailView.as_view(), name='brujka_detail'),
    path('brujkalar/search/', views.BrujkaSearchAPIView.as_view(), name='brujka_search'),

    # Additional orders
    path('additional/', views.AdditionalOrderListView.as_view(), name='additional_order_list'),
    path('additional/create/', views.AdditionalOrderCreateView.as_view(), name='additional_order_create'),
    path('additional/<int:pk>/', views.AdditionalOrderDetailView.as_view(), name='additional_order_detail'),
    path('additional/<int:pk>/update/', views.AdditionalOrderUpdateView.as_view(), name='additional_order_update'),
    path('additional/<int:pk>/delete/', views.AdditionalOrderDeleteView.as_view(), name='additional_order_delete'),
    path('additional/<int:pk>/set-status/', views.AdditionalOrderSetStatusView.as_view(), name='additional_set_status'),
    path('additional/<int:pk>/hom/add/', views.AdditionalHomLogCreateView.as_view(), name='additional_hom_add'),
    path('additional/<int:pk>/hom/<int:log_pk>/delete/', views.AdditionalHomLogDeleteView.as_view(), name='additional_hom_delete'),
    path('additional/<int:pk>/tayor/add/', views.AdditionalTayorLogCreateView.as_view(), name='additional_tayor_add'),
    path('additional/<int:pk>/tayor/<int:log_pk>/delete/', views.AdditionalTayorLogDeleteView.as_view(), name='additional_tayor_delete'),
]
