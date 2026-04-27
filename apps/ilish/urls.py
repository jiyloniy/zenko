from django.urls import path
from . import views

app_name = 'ilish'

urlpatterns = [
    # Jarayonlar
    path('', views.IlishJarayonListView.as_view(), name='jarayon_list'),
    path('<int:pk>/', views.IlishJarayonDetailView.as_view(), name='jarayon_detail'),
    path('<int:pk>/set-status/', views.IlishJarayonSetStatusView.as_view(), name='jarayon_set_status'),
    path('<int:pk>/log/add/', views.IlishLogCreateView.as_view(), name='log_create'),
    path('<int:pk>/log/bulk/', views.BulkLogCreateView.as_view(), name='log_bulk'),
    path('<int:pk>/log/<int:log_pk>/delete/', views.IlishLogDeleteView.as_view(), name='log_delete'),

    # Vishilkalar
    path('vishilkalar/', views.VishilkaListView.as_view(), name='vishilka_list'),
    path('vishilkalar/create/', views.VishilkaCreateView.as_view(), name='vishilka_create'),
    path('vishilkalar/<int:pk>/edit/', views.VishilkaUpdateView.as_view(), name='vishilka_update'),
    path('vishilkalar/<int:pk>/delete/', views.VishilkaDeleteView.as_view(), name='vishilka_delete'),

    # Statistika
    path('stats/', views.IlishStatsView.as_view(), name='stats'),
]
