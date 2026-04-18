from django.urls import path

from apps.attendance import view2

app_name = 'attendance'

urlpatterns = [
    # QR code image
    path('qr/<int:user_id>/', view2.QRCodeImageView.as_view(), name='qr_image'),

    # Combined kiosk page
    path('', view2.AttendanceKioskView.as_view(), name='kiosk'),

    # Legacy routes (redirect to kiosk)
    path('check-in/', view2.CheckInPageView.as_view(), name='check_in'),
    path('check-out/', view2.CheckOutPageView.as_view(), name='check_out'),

    # Smart API (single endpoint)
    path('api/scan/', view2.AttendanceScanAPIView.as_view(), name='api_scan'),

    # Legacy API endpoints
    path('api/check-in/', view2.CheckInAPIView.as_view(), name='api_check_in'),
    path('api/check-out/', view2.CheckOutAPIView.as_view(), name='api_check_out'),
]
