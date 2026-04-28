from django.urls import path
from . import views

app_name = 'sepish'

urlpatterns = [
    path('', views.SepishJarayonListView.as_view(), name='jarayon_list'),
    path('<int:pk>/', views.SepishJarayonDetailView.as_view(), name='jarayon_detail'),
    path('<int:pk>/set-status/', views.SepishJarayonSetStatusView.as_view(), name='jarayon_set_status'),
    path('<int:pk>/log/add/', views.SepishLogCreateView.as_view(), name='log_create'),
    path('<int:pk>/log/quick/', views.SepishQuickLogView.as_view(), name='log_quick'),
    path('<int:pk>/log/<int:log_pk>/edit/', views.SepishLogUpdateView.as_view(), name='log_update'),
    path('<int:pk>/log/<int:log_pk>/delete/', views.SepishLogDeleteView.as_view(), name='log_delete'),

    path('kraskalar/', views.KraskaListView.as_view(), name='kraska_list'),
    path('kraskalar/create/', views.KraskaCreateView.as_view(), name='kraska_create'),
    path('kraskalar/<int:pk>/edit/', views.KraskaUpdateView.as_view(), name='kraska_update'),
    path('kraskalar/<int:pk>/delete/', views.KraskaDeleteView.as_view(), name='kraska_delete'),

    path('stats/', views.SepishStatsView.as_view(), name='stats'),
]
