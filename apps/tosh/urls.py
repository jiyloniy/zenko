from django.urls import path
from . import views

app_name = 'tosh'

urlpatterns = [
    # ── Tosh qadash jarayonlari ──
    path('', views.ToshJarayonListView.as_view(), name='jarayon_list'),
    path('<int:pk>/', views.ToshJarayonDetailView.as_view(), name='jarayon_detail'),
    path('<int:pk>/set-status/', views.ToshJarayonSetStatusView.as_view(), name='jarayon_set_status'),

    # ── Log (hodim bo'yicha) ──
    path('<int:pk>/log/add/', views.ToshLogCreateView.as_view(), name='log_create'),
    path('<int:pk>/log/bulk/', views.ToshBulkLogCreateView.as_view(), name='log_bulk'),
    path('<int:pk>/log/<int:log_pk>/delete/', views.ToshLogDeleteView.as_view(), name='log_delete'),

    # ── Kley rasxod — alohida bo'lim ──
    path('kley/', views.KleyRasxodListView.as_view(), name='kley_list'),
    path('kley/<int:pk>/add/', views.KleyRasxodCreateView.as_view(), name='kley_create'),
    path('kley/<int:pk>/delete/', views.KleyRasxodDeleteView.as_view(), name='kley_delete'),

    # ── Tosh rasxod — alohida bo'lim ──
    path('tosh-rasxod/', views.ToshRasxodListView.as_view(), name='tosh_rasxod_list'),
    path('tosh-rasxod/<int:pk>/add/', views.ToshRasxodCreateView.as_view(), name='tosh_rasxod_create'),
    path('tosh-rasxod/<int:pk>/delete/', views.ToshRasxodDeleteView.as_view(), name='tosh_rasxod_delete'),

    # ── Toshlar ro'yhati (CRUD) ──
    path('toshlar/', views.ToshListView.as_view(), name='tosh_list'),
    path('toshlar/create/', views.ToshCreateView.as_view(), name='tosh_create'),
    path('toshlar/<int:pk>/edit/', views.ToshUpdateView.as_view(), name='tosh_update'),
    path('toshlar/<int:pk>/delete/', views.ToshDeleteView.as_view(), name='tosh_delete'),

    # ── Statistika ──
    path('stats/', views.ToshStatsView.as_view(), name='stats'),
]
