from django.urls import path

from apps.attendance import views

app_name = 'attendance'

urlpatterns = [
    # QR code image
    path('qr/<int:user_id>/', views.QRCodeImageView.as_view(), name='qr_image'),

    # Combined kiosk page
    path('', views.AttendanceKioskView.as_view(), name='kiosk'),

    # Legacy routes (redirect to kiosk)
    path('check-in/', views.CheckInPageView.as_view(), name='check_in'),
    path('check-out/', views.CheckOutPageView.as_view(), name='check_out'),

    # Smart API (single endpoint)
    path('api/scan/', views.AttendanceScanAPIView.as_view(), name='api_scan'),

    # Legacy API endpoints
    path('api/check-in/', views.CheckInAPIView.as_view(), name='api_check_in'),
    path('api/check-out/', views.CheckOutAPIView.as_view(), name='api_check_out'),
]
