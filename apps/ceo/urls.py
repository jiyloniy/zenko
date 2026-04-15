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
]
