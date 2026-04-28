from django.urls import path
from . import views

app_name = 'boyash'

urlpatterns = [
    path('', views.BoyashJarayonListView.as_view(), name='jarayon_list'),
    path('<int:pk>/', views.BoyashJarayonDetailView.as_view(), name='jarayon_detail'),
    path('<int:pk>/set-status/', views.BoyashJarayonSetStatusView.as_view(), name='jarayon_set_status'),
    path('<int:pk>/log/add/', views.BoyashLogCreateView.as_view(), name='log_create'),
    path('<int:pk>/log/<int:log_pk>/delete/', views.BoyashLogDeleteView.as_view(), name='log_delete'),
    path('stats/', views.BoyashStatsView.as_view(), name='stats'),
]
