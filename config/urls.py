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
    path('users/', include('apps.users.urls')),
    path('casting/', include('apps.casting.urls')),
    path('ilish/', include('apps.ilish.urls')),
    path('boyash/', include('apps.boyash.urls')),
    path('sepish/', include('apps.sepish.urls')),
    path('tosh/', include('apps.tosh.urls')),
    path('shop/', include('apps.shop.urls')),
    path('', include('apps.manage.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


