from django.urls import path

from apps.ceo import views

app_name = 'ceo'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Users
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<int:pk>/reset-password/', views.UserResetPasswordView.as_view(), name='user_reset_password'),

    # Roles
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/create/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<int:pk>/edit/', views.RoleUpdateView.as_view(), name='role_update'),
    path('roles/<int:pk>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),

    # Departments
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_update'),
    path('departments/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),

    # Shifts
    path('shifts/', views.ShiftListView.as_view(), name='shift_list'),
    path('shifts/create/', views.ShiftCreateView.as_view(), name='shift_create'),
    path('shifts/<int:pk>/edit/', views.ShiftUpdateView.as_view(), name='shift_update'),
    path('shifts/<int:pk>/delete/', views.ShiftDeleteView.as_view(), name='shift_delete'),

    # Attendance
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/create/', views.AttendanceCreateView.as_view(), name='attendance_create'),
    path('attendance/bulk/', views.BulkAttendanceView.as_view(), name='attendance_bulk'),
    path('attendance/bulk-delete/', views.AttendanceBulkDeleteView.as_view(), name='attendance_bulk_delete'),
    path('attendance/mark-absent/', views.MarkAbsentView.as_view(), name='mark_absent'),
    path('attendance/<int:pk>/edit/', views.AttendanceUpdateView.as_view(), name='attendance_update'),
    path('attendance/<int:pk>/delete/', views.AttendanceDeleteView.as_view(), name='attendance_delete'),
    path('attendance/stats/', views.AttendanceStatsView.as_view(), name='attendance_stats'),
    path('attendance/stats/shift/<int:pk>/', views.ShiftStatsDetailView.as_view(), name='shift_stats_detail'),
    path('attendance/stats/dept/<int:pk>/', views.DeptStatsDetailView.as_view(), name='dept_stats_detail'),
    path('attendance/stats/user/<int:pk>/', views.UserStatsDetailView.as_view(), name='user_stats_detail'),

    # QR Cards
    path('users/<int:pk>/qr/', views.QRCardView.as_view(), name='qr_card'),
    path('qr-cards/', views.QRCardAllView.as_view(), name='qr_cards_all'),

    # Salary
    path('salary/', views.SalaryListView.as_view(), name='salary_list'),
    path('salary/<int:pk>/', views.SalaryDetailView.as_view(), name='salary_detail'),

    # Quyish loglar (CEO)
    path('orders/<int:pk>/log/', views.OrderLogView.as_view(), name='order_log'),
    path('orders/<int:pk>/hom/add/', views.HomLogCreateView.as_view(), name='hom_log_add'),
    path('orders/<int:pk>/hom/<int:log_pk>/edit/', views.HomLogEditView.as_view(), name='hom_log_edit'),
    path('orders/<int:pk>/hom/<int:log_pk>/delete/', views.HomLogDeleteView.as_view(), name='hom_log_delete'),
    path('orders/<int:pk>/tayor/add/', views.TayorLogCreateView.as_view(), name='tayor_log_add'),
    path('orders/<int:pk>/tayor/<int:log_pk>/edit/', views.TayorLogEditView.as_view(), name='tayor_log_edit'),
    path('orders/<int:pk>/tayor/<int:log_pk>/delete/', views.TayorLogDeleteView.as_view(), name='tayor_log_delete'),

    # Additional Orders
    path('additional/', views.CeoAdditionalOrderListView.as_view(), name='additional_order_list'),
    path('additional/create/', views.CeoAdditionalOrderCreateView.as_view(), name='additional_order_create'),
    path('additional/<int:pk>/', views.CeoAdditionalOrderDetailView.as_view(), name='additional_order_detail'),
    path('additional/<int:pk>/set-status/', views.CeoAdditionalOrderSetStatusView.as_view(), name='additional_set_status'),
    path('additional/<int:pk>/delete/', views.CeoAdditionalOrderDeleteView.as_view(), name='additional_order_delete'),
    path('additional/<int:pk>/hom/add/', views.CeoAdditionalHomLogCreateView.as_view(), name='additional_hom_add'),
    path('additional/<int:pk>/hom/<int:log_pk>/delete/', views.CeoAdditionalHomLogDeleteView.as_view(), name='additional_hom_delete'),

    # Rasxod
    path('rasxod/', views.CeoRasxodListView.as_view(), name='rasxod_list'),
    path('rasxod/add/', views.CeoRasxodCreateView.as_view(), name='rasxod_add'),
    path('rasxod/<int:pk>/delete/', views.CeoRasxodDeleteView.as_view(), name='rasxod_delete'),
    path('zamaklar/', views.CeoZamakListView.as_view(), name='zamak_list'),
    path('zamaklar/<int:pk>/delete/', views.CeoZamakDeleteView.as_view(), name='zamak_delete'),

    # Stanoklar
    path('stanoklar/', views.StanokListView.as_view(), name='stanok_list'),
    path('stanoklar/create/', views.StanokCreateView.as_view(), name='stanok_create'),
    path('stanoklar/<int:pk>/edit/', views.StanokUpdateView.as_view(), name='stanok_edit'),
    path('stanoklar/<int:pk>/delete/', views.StanokDeleteView.as_view(), name='stanok_delete'),
]
