"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.ceo.views import LoginView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('attendance/', include('apps.attendance.urls')),
    path('ceo/', include('apps.ceo.urls')),
    path('boss/', include('apps.boss.urls')),
    path('order/', include('apps.order.urls')),
    path('casting/', include('apps.casting.urls')),
    path('attach/', include('apps.attach.urls')),
    path('spray/', include('apps.spray.urls')),
    path('paint/', include('apps.paint.urls')),
    path('stone/', include('apps.stone.urls')),
    path('assembly/', include('apps.assembly.urls')),
    path('pack/', include('apps.pack.urls')),
    path('users/', include('apps.users.urls')),
    path('', include('apps.manage.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
