from django.urls import path
from apps.manage import views

app_name = 'manage'

urlpatterns = [
    path('', views.home, name='home'),
]
