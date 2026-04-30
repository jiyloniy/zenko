import datetime
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.ceo.forms import (
    AttendanceForm,
    BulkAttendanceForm,
    DepartmentForm,
    RoleForm,
    ShiftForm,
    UserCreateForm,
    UserUpdateForm,
)
from apps.users.models import Branch, Department, Role, Shift, User
from apps.attendance.models import Attendance
from apps.attendance.views import generate_qr_token


class CEORequiredMixin(LoginRequiredMixin):
    """Faqat CEO rolidagi foydalanuvchiga ruxsat."""
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.role and request.user.role.name == 'CEO'):
            if not request.user.is_superuser:
                messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
                return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_branch(self):
        """CEO ga biriktirilgan filial."""
        return getattr(self.request.user, 'branch', None)


# ── Auth ──

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return self._redirect_by_role(request.user)
        return render(request, 'ceo/login.html')
    
    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return self._redirect_by_role(user)
        return render(request, 'ceo/login.html', {
            'error': 'Username yoki parol noto\u2018g\u2018ri.',
        })

    def _redirect_by_role(self, user):
        role_name = user.role.name if user.role else None
        if role_name == 'BOSS':
            return redirect('boss:dashboard')
        if role_name == 'CASTINGMANAGER':
            return redirect('casting:order_list')
        if role_name == 'ATTACHMANAGER':
            return redirect('ilish:jarayon_list')
        if role_name == 'BOYASHMANAGER':
            return redirect('boyash:jarayon_list')
        if role_name == 'SPRAYMANAGER':
            return redirect('sepish:jarayon_list')
        if role_name == 'TOSHMANAGER':
            return redirect('tosh:jarayon_list')
        if role_name == 'SHOPMANAGER':
            return redirect('shop:dashboard')
        return redirect('ceo:dashboard')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


# ── Dashboard ──

class DashboardView(CEORequiredMixin, View):
    def get(self, request):
        branch = request.user.branch
        if branch:
            users = User.objects.filter(branch=branch)
            departments = Department.objects.filter(branch=branch)
            shifts = Shift.objects.filter(branch=branch)
        else:
            users = User.objects.none()
            departments = Department.objects.none()
            shifts = Shift.objects.none()
        context = {
            'active_nav': 'dashboard',
            'branch': branch,
            'total_users': users.count(),
            'total_roles': Role.objects.count(),
            'total_departments': departments.count(),
            'total_shifts': shifts.count(),
            'recent_users': users.select_related('role', 'department', 'shift')[:10],
        }
        return render(request, 'ceo/dashboard.html', context)


# ── Users CRUD ──

class UserListView(CEORequiredMixin, ListView):
    model = User
    template_name = 'ceo/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        branch = self.get_branch()
        qs = User.objects.select_related('role', 'department', 'shift')
        if branch:
            qs = qs.filter(branch=branch)
        # Filterlar
        role_f   = self.request.GET.get('role', '').strip()
        dept_f   = self.request.GET.get('department', '').strip()
        status_f = self.request.GET.get('status', '').strip()
        vip_f    = self.request.GET.get('vip', '').strip()
        search_f = self.request.GET.get('search', '').strip()
        if role_f:
            qs = qs.filter(role_id=role_f)
        if dept_f:
            qs = qs.filter(department_id=dept_f)
        if status_f == 'active':
            qs = qs.filter(is_active=True)
        elif status_f == 'inactive':
            qs = qs.filter(is_active=False)
        if vip_f == '1':
            qs = qs.filter(is_vip=True)
        elif vip_f == '0':
            qs = qs.filter(is_vip=False)
        if search_f:
            qs = qs.filter(name__icontains=search_f)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = self.get_branch()
        ctx['active_nav'] = 'users'
        ctx['branch'] = branch
        ctx['roles'] = Role.objects.all()
        ctx['departments'] = Department.objects.filter(branch=branch) if branch else Department.objects.all()
        ctx['filter_role']   = self.request.GET.get('role', '')
        ctx['filter_dept']   = self.request.GET.get('department', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        ctx['filter_vip']    = self.request.GET.get('vip', '')
        ctx['filter_search'] = self.request.GET.get('search', '')
        return ctx


class UserCreateView(CEORequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'ceo/user_form.html'
    success_url = reverse_lazy('ceo:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = self.get_branch()
        ctx.update({
            'active_nav': 'users',
            'title': 'Yangi hodim',
            'branch': branch,
            'roles': Role.objects.all(),
            'departments': Department.objects.filter(branch=branch) if branch else Department.objects.none(),
            'shifts': Shift.objects.filter(branch=branch) if branch else Shift.objects.none(),
        })
        return ctx

    def form_valid(self, form):
        branch = self.get_branch()
        if branch:
            form.instance.branch = branch
        messages.success(self.request, 'Hodim muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class UserUpdateView(CEORequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'ceo/user_form.html'
    success_url = reverse_lazy('ceo:user_list')

    def get_queryset(self):
        branch = self.get_branch()
        qs = User.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = self.get_branch()
        ctx.update({
            'active_nav': 'users',
            'title': f'{self.object.name} — tahrirlash',
            'branch': branch,
            'roles': Role.objects.all(),
            'departments': Department.objects.filter(branch=branch) if branch else Department.objects.none(),
            'shifts': Shift.objects.filter(branch=branch) if branch else Shift.objects.none(),
        })
        return ctx

    def form_valid(self, form):
        branch = self.get_branch()
        if branch:
            form.instance.branch = branch
        messages.success(self.request, 'Hodim muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class UserResetPasswordView(CEORequiredMixin, View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return render(request, 'ceo/user_reset_password.html', {
            'employee': user,
            'active_nav': 'users',
        })

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        new_password = request.POST.get('new_password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()

        if not new_password:
            messages.error(request, 'Parol bo\'sh bo\'lishi mumkin emas.')
            return render(request, 'ceo/user_reset_password.html', {
                'employee': user,
                'active_nav': 'users',
            })
        if new_password != confirm:
            messages.error(request, 'Parollar mos kelmadi.')
            return render(request, 'ceo/user_reset_password.html', {
                'employee': user,
                'active_nav': 'users',
            })
        if len(new_password) < 4:
            messages.error(request, 'Parol kamida 4 ta belgidan iborat bo\'lishi kerak.')
            return render(request, 'ceo/user_reset_password.html', {
                'employee': user,
                'active_nav': 'users',
            })

        user.set_password(new_password)
        user.save()
        messages.success(request, f'{user.name} uchun parol muvaffaqiyatli yangilandi.')
        return redirect('ceo:user_update', pk=pk)


class UserDeleteView(CEORequiredMixin, DeleteView):
    model = User
    template_name = 'ceo/confirm_delete.html'
    success_url = reverse_lazy('ceo:user_list')

    def get_queryset(self):
        branch = self.get_branch()
        qs = User.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'users', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Hodim o\'chirildi.')
        return super().form_valid(form)


# ── Roles CRUD ──

class RoleListView(CEORequiredMixin, ListView):
    model = Role
    template_name = 'ceo/role_list.html'
    context_object_name = 'roles'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'roles'
        return ctx


class RoleCreateView(CEORequiredMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = 'ceo/role_form.html'
    success_url = reverse_lazy('ceo:role_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'roles',
            'title': 'Yangi rol',
            'cancel_url': self.success_url,
        })
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Rol muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class RoleUpdateView(CEORequiredMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = 'ceo/role_form.html'
    success_url = reverse_lazy('ceo:role_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'roles',
            'title': f'{self.object.name} — tahrirlash',
            'cancel_url': self.success_url,
        })
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Rol muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class RoleDeleteView(CEORequiredMixin, DeleteView):
    model = Role
    template_name = 'ceo/confirm_delete.html'
    success_url = reverse_lazy('ceo:role_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'roles', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Rol o\'chirildi.')
        return super().form_valid(form)


# ── Departments CRUD ──

class DepartmentListView(CEORequiredMixin, ListView):
    model = Department
    template_name = 'ceo/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        branch = self.get_branch()
        qs = Department.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'departments'
        ctx['branch'] = self.get_branch()
        return ctx


class DepartmentCreateView(CEORequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'ceo/department_form.html'
    success_url = reverse_lazy('ceo:department_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'departments',
            'title': 'Yangi bo\'lim',
            'cancel_url': self.success_url,
            'branch': self.get_branch(),
        })
        return ctx

    def form_valid(self, form):
        branch = self.get_branch()
        if branch:
            form.instance.branch = branch
        messages.success(self.request, 'Bo\'lim muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class DepartmentUpdateView(CEORequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'ceo/department_form.html'
    success_url = reverse_lazy('ceo:department_list')

    def get_queryset(self):
        branch = self.get_branch()
        qs = Department.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'departments',
            'title': f'{self.object.name} — tahrirlash',
            'cancel_url': self.success_url,
            'branch': self.get_branch(),
        })
        return ctx

    def form_valid(self, form):
        branch = self.get_branch()
        if branch:
            form.instance.branch = branch
        messages.success(self.request, 'Bo\'lim muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class DepartmentDeleteView(CEORequiredMixin, DeleteView):
    model = Department
    template_name = 'ceo/confirm_delete.html'
    success_url = reverse_lazy('ceo:department_list')

    def get_queryset(self):
        branch = self.get_branch()
        qs = Department.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'departments', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Bo\'lim o\'chirildi.')
        return super().form_valid(form)


# ── Shifts CRUD ──

class ShiftListView(CEORequiredMixin, ListView):
    model = Shift
    template_name = 'ceo/shift_list.html'
    context_object_name = 'shifts'

    def get_queryset(self):
        branch = self.get_branch()
        qs = Shift.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'shifts'
        ctx['branch'] = self.get_branch()
        return ctx


class ShiftCreateView(CEORequiredMixin, CreateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'ceo/shift_form.html'
    success_url = reverse_lazy('ceo:shift_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'shifts',
            'title': 'Yangi smena',
            'cancel_url': self.success_url,
            'branch': self.get_branch(),
        })
        return ctx

    def form_valid(self, form):
        branch = self.get_branch()
        if branch:
            form.instance.branch = branch
        messages.success(self.request, 'Smena muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class ShiftUpdateView(CEORequiredMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'ceo/shift_form.html'
    success_url = reverse_lazy('ceo:shift_list')

    def get_queryset(self):
        branch = self.get_branch()
        qs = Shift.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'shifts',
            'title': f'{self.object.name} — tahrirlash',
            'cancel_url': self.success_url,
            'branch': self.get_branch(),
        })
        return ctx

    def form_valid(self, form):
        branch = self.get_branch()
        if branch:
            form.instance.branch = branch
        messages.success(self.request, 'Smena muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class ShiftDeleteView(CEORequiredMixin, DeleteView):
    model = Shift
    template_name = 'ceo/confirm_delete.html'
    success_url = reverse_lazy('ceo:shift_list')

    def get_queryset(self):
        branch = self.get_branch()
        qs = Shift.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'shifts', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Smena o\'chirildi.')
        return super().form_valid(form)


# ── Attendance ──

class AttendanceListView(CEORequiredMixin, ListView):
    model = Attendance
    template_name = 'ceo/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 50

    def get_queryset(self):
        branch = self.get_branch()
        qs = Attendance.objects.select_related(
            'user', 'user__shift', 'effective_shift',
        )
        if branch:
            qs = qs.filter(branch=branch)

        date_filter = self.request.GET.get('date')
        status_filter = self.request.GET.get('status')
        user_filter = self.request.GET.get('user')
        shift_filter = self.request.GET.get('shift')

        if date_filter:
            qs = qs.filter(date=date_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if user_filter:
            qs = qs.filter(user_id=user_filter)
        if shift_filter:
            # Filter by effective_shift (detected) OR user's assigned shift
            qs = qs.filter(
                Q(effective_shift_id=shift_filter) | Q(user__shift_id=shift_filter)
            )

        return qs

    def _annotate_attendance(self, att):
        """Har bir davomat yozuviga smena tahlili ma'lumotlarini qo'shadi."""
        from apps.attendance.view2 import (
            LATE_GRACE_MINUTES, CHECKOUT_GRACE_MINUTES,
            _shift_start_dt, _shift_end_dt_from_start,
        )
        shift = att.effective_shift or att.user.shift if att.user else None
        info = {
            'shift': shift,
            'shift_mismatch': (
                att.effective_shift and att.user.shift and
                att.effective_shift_id != att.user.shift_id
            ),
            'late_minutes': None,
            'early_minutes': None,
            'early_leave_minutes': None,
            'grace_applied': False,
            'billing_in': att.effective_check_in or att.check_in,
            'billing_out': att.check_out,
            'actual_in': att.check_in,
            'actual_out': att.actual_check_out,
        }
        if shift and att.check_in:
            start_dt = _shift_start_dt(shift, att.date)
            if start_dt:
                end_dt = _shift_end_dt_from_start(shift, start_dt)
                diff_in = int(
                    (timezone.localtime(att.check_in) - timezone.localtime(start_dt)).total_seconds() / 60
                )
                if diff_in < 0:
                    info['early_minutes'] = abs(diff_in)
                elif diff_in <= LATE_GRACE_MINUTES:
                    info['late_minutes'] = diff_in
                else:
                    info['late_minutes'] = diff_in

                if att.actual_check_out and end_dt:
                    diff_out = int(
                        (timezone.localtime(att.actual_check_out) - timezone.localtime(end_dt)).total_seconds() / 60
                    )
                    if 0 <= diff_out <= CHECKOUT_GRACE_MINUTES:
                        info['grace_applied'] = True
                    elif diff_out < 0:
                        info['early_leave_minutes'] = abs(diff_out)

        att.shift_info = info
        return att

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = self.get_branch()
        today = timezone.localtime().date()

        # Bugungi statistikalar
        today_qs = Attendance.objects.filter(date=today)
        if branch:
            today_qs = today_qs.filter(branch=branch)

        total_today = today_qs.count()
        present_today = today_qs.filter(status='present').count()
        late_today = today_qs.filter(status='late').count()
        absent_today = today_qs.filter(status='absent').count()
        active_now = today_qs.filter(check_in__isnull=False, check_out__isnull=True).count()

        # Smena bo'yicha statistika (effective_shift yoki user.shift bo'yicha)
        shift_stats = []
        shifts_qs = Shift.objects.filter(branch=branch) if branch else Shift.objects.none()
        for shift in shifts_qs:
            shift_today = today_qs.filter(
                Q(effective_shift=shift) | Q(user__shift=shift, effective_shift__isnull=True)
            )
            shift_stats.append({
                'shift': shift,
                'total': shift_today.count(),
                'present': shift_today.filter(status='present').count(),
                'late': shift_today.filter(status='late').count(),
                'absent': shift_today.filter(status='absent').count(),
            })

        # Total hodimlar soni (bugun kelishi kerak bo'lganlar)
        total_employees = User.objects.filter(branch=branch, is_active=True).count() if branch else 0

        # Har bir davomat yozuviga smena tahlili qo'shamiz
        for att in ctx.get('attendances', []):
            self._annotate_attendance(att)

        ctx.update({
            'active_nav': 'attendance',
            'branch': branch,
            'filter_date': self.request.GET.get('date', ''),
            'filter_status': self.request.GET.get('status', ''),
            'filter_user': self.request.GET.get('user', ''),
            'filter_shift': self.request.GET.get('shift', ''),
            'status_choices': Attendance.STATUS_CHOICES,
            'users': User.objects.filter(branch=branch, is_active=True) if branch else User.objects.none(),
            'shifts': shifts_qs,
            'today': today,
            'today_iso': today.isoformat(),
            'total_today': total_today,
            'present_today': present_today,
            'late_today': late_today,
            'absent_today': absent_today,
            'active_now': active_now,
            'total_employees': total_employees,
            'attendance_rate': round((total_today / total_employees * 100) if total_employees else 0),
            'shift_stats': shift_stats,
            'LATE_GRACE_MINUTES': 15,
            'CHECKOUT_GRACE_MINUTES': 30,
        })
        return ctx


def _build_users_json(branch):
    import json
    users = User.objects.filter(branch=branch, is_active=True).select_related('shift') if branch else User.objects.none()
    data = {}
    for u in users:
        sh = u.shift
        is_night = bool(sh and sh.start_time and sh.end_time and sh.end_time <= sh.start_time)
        data[str(u.pk)] = {
            'shift_id':    sh.pk if sh else '',
            'shift_start': sh.start_time.strftime('%H:%M') if sh and sh.start_time else '',
            'shift_end':   sh.end_time.strftime('%H:%M')   if sh and sh.end_time   else '',
            'is_night':    is_night,
        }
    return json.dumps(data)


class AttendanceCreateView(CEORequiredMixin, View):
    """Qo'lda bitta davomat yozuvi qo'shish."""

    def get(self, request):
        branch = self.get_branch()
        form = AttendanceForm(branch=branch)
        return render(request, 'ceo/attendance_form.html', {
            'active_nav': 'attendance', 'form': form, 'title': "Davomat qo'shish",
            'users_json': self._users_json(branch),
        })

    def post(self, request):
        branch = self.get_branch()
        form = AttendanceForm(request.POST, branch=branch)
        if form.is_valid():
            att = form.save(commit=False)
            att.branch = branch
            att.save()
            messages.success(request, f'{att.user.name} uchun davomat yozildi.')
            return redirect('ceo:attendance_list')
        return render(request, 'ceo/attendance_form.html', {
            'active_nav': 'attendance', 'form': form, 'title': "Davomat qo'shish",
            'users_json': self._users_json(branch),
        })

    def _users_json(self, branch):
        return _build_users_json(branch)


class AttendanceUpdateView(CEORequiredMixin, View):
    """Davomat yozuvini tahrirlash."""

    def get(self, request, pk):
        branch = self.get_branch()
        att = get_object_or_404(Attendance, pk=pk, branch=branch) if branch else get_object_or_404(Attendance, pk=pk)
        form = AttendanceForm(instance=att, branch=branch)
        return render(request, 'ceo/attendance_form.html', {
            'active_nav': 'attendance', 'form': form, 'title': 'Davomatni tahrirlash',
            'edit_mode': True, 'attendance': att,
            'users_json': _build_users_json(branch),
        })

    def post(self, request, pk):
        branch = self.get_branch()
        att = get_object_or_404(Attendance, pk=pk, branch=branch) if branch else get_object_or_404(Attendance, pk=pk)
        form = AttendanceForm(request.POST, instance=att, branch=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Davomat yangilandi.')
            return redirect('ceo:attendance_list')
        return render(request, 'ceo/attendance_form.html', {
            'active_nav': 'attendance', 'form': form, 'title': 'Davomatni tahrirlash',
            'edit_mode': True, 'attendance': att,
            'users_json': _build_users_json(branch),
        })


class AttendanceDeleteView(CEORequiredMixin, View):
    """Davomat yozuvini o'chirish."""

    def post(self, request, pk):
        branch = self.get_branch()
        att = get_object_or_404(Attendance, pk=pk, branch=branch) if branch else get_object_or_404(Attendance, pk=pk)
        name = att.user.name
        att.delete()
        messages.success(request, f'{name} davomati o\'chirildi.')
        return redirect('ceo:attendance_list')


class AttendanceBulkDeleteView(CEORequiredMixin, View):
    """Jadvaldan tanlangan davomat yozuvlarini o'chirish."""

    def post(self, request):
        branch = self.get_branch()
        raw_ids = request.POST.getlist('ids')
        next_url = request.POST.get('next', '').strip()
        if not raw_ids:
            messages.warning(request, 'Hech qanday qator tanlanmagan.')
            return self._redirect_back(request, next_url)

        try:
            ids = [int(x) for x in raw_ids if str(x).isdigit()]
        except ValueError:
            ids = []

        if not ids:
            messages.warning(request, 'Noto\'g\'ri tanlov.')
            return self._redirect_back(request, next_url)

        qs = Attendance.objects.filter(pk__in=ids)
        if branch:
            qs = qs.filter(branch=branch)
        n = qs.count()
        qs.delete()
        messages.success(request, f'{n} ta yozuv o\'chirildi.')
        return self._redirect_back(request, next_url)

    def _redirect_back(self, request, next_url):
        if next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)
        return redirect('ceo:attendance_list')


class BulkAttendanceView(CEORequiredMixin, View):
    """Bir nechta hodimga bir vaqtda davomat belgilash."""

    def get(self, request):
        branch = self.get_branch()
        form = BulkAttendanceForm(branch=branch)
        return render(request, 'ceo/attendance_bulk.html', {
            'active_nav': 'attendance', 'form': form,
        })

    def post(self, request):
        branch = self.get_branch()
        form = BulkAttendanceForm(request.POST, branch=branch)
        if form.is_valid():
            date = form.cleaned_data['date']
            users = form.cleaned_data['users']
            mode = form.cleaned_data['mode']

            if mode == BulkAttendanceForm.MODE_ABSENT:
                created = 0
                for user in users:
                    exists = Attendance.objects.filter(user=user, date=date, branch=branch).exists()
                    if not exists:
                        Attendance.objects.create(
                            user=user,
                            branch=branch,
                            date=date,
                            status=Attendance.STATUS_ABSENT,
                        )
                        created += 1
                messages.success(request, f'{created} hodim "Kelmadi" deb belgilandi.')
                return redirect('ceo:attendance_list')

            # MODE_TIMES: bir xil kirish/chiqish — mavjud yozuvni admin yangilashi (QR + bulk)
            t_in = form.cleaned_data['check_in_time']
            t_out = form.cleaned_data.get('check_out_time')
            checkout_blank = form.cleaned_data.get('_checkout_blank', True)
            tz = timezone.get_current_timezone()
            dt_in = timezone.make_aware(datetime.datetime.combine(date, t_in), tz)
            dt_out = None
            if not checkout_blank and t_out is not None:
                dt_out = timezone.make_aware(datetime.datetime.combine(date, t_out), tz)
                if dt_out <= dt_in:
                    dt_out = timezone.make_aware(
                        datetime.datetime.combine(date + datetime.timedelta(days=1), t_out),
                        tz,
                    )

            from apps.attendance.view2 import (
                _detect_effective_shift,
                _compute_check_in_info,
                _compute_check_out_info,
                _shift_start_dt,
                _shift_end_dt_from_start,
            )

            created = 0
            updated = 0
            for user in users:
                # Effective maydonlarni hisoblash
                eff_shift, start_dt, _ = _detect_effective_shift(user, dt_in)
                in_info = _compute_check_in_info(actual_in=dt_in, start_dt=start_dt)
                effective_in = in_info['effective_in']
                status = in_info['status'] if in_info['status'] != 'early' else Attendance.STATUS_PRESENT

                effective_out = dt_out
                actual_out = dt_out
                if dt_out and eff_shift and eff_shift.start_time and eff_shift.end_time:
                    check_in_date = timezone.localtime(dt_in).date()
                    s_dt = _shift_start_dt(eff_shift, check_in_date)
                    end_dt = _shift_end_dt_from_start(eff_shift, s_dt)
                    out_info = _compute_check_out_info(actual_out=dt_out, end_dt=end_dt)
                    effective_out = out_info['effective_out']

                att = Attendance.objects.filter(user=user, date=date, branch=branch).first()
                if att is None:
                    Attendance.objects.create(
                        user=user,
                        branch=branch,
                        date=date,
                        check_in=dt_in,
                        check_out=effective_out,
                        actual_check_out=actual_out if not checkout_blank else None,
                        effective_check_in=effective_in,
                        effective_shift=eff_shift,
                        status=status,
                    )
                    created += 1
                    continue
                att.check_in = dt_in
                att.effective_check_in = effective_in
                att.effective_shift = eff_shift
                att.status = status
                if not checkout_blank:
                    att.check_out = effective_out
                    att.actual_check_out = actual_out
                att.save()
                updated += 1
            parts = []
            if created:
                parts.append(f'yangi: {created}')
            if updated:
                parts.append(f'yangilandi: {updated}')
            messages.success(
                request,
                'Ommaviy vaqtlar: ' + (', '.join(parts) if parts else 'o\'zgarish yo\'q'),
            )
            return redirect('ceo:attendance_list')
        return render(request, 'ceo/attendance_bulk.html', {
            'active_nav': 'attendance', 'form': form,
        })


class MarkAbsentView(CEORequiredMixin, View):
    """Kelmagan hodimlarni avtomatik 'absent' deb belgilash."""

    def post(self, request):
        branch = self.get_branch()
        date_str = request.POST.get('date', '')
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            target_date = timezone.localtime().date()

        if not branch:
            messages.error(request, 'Filial topilmadi.')
            return redirect('ceo:attendance_list')

        all_users = User.objects.filter(branch=branch, is_active=True).select_related('shift')
        attended_ids = set(
            Attendance.objects.filter(
                branch=branch, date=target_date,
            ).values_list('user_id', flat=True)
        )

        created = 0
        for user in all_users:
            if user.pk not in attended_ids:
                Attendance.objects.create(
                    user=user,
                    branch=branch,
                    date=target_date,
                    status=Attendance.STATUS_ABSENT,
                )
                created += 1

        messages.success(request, f'{target_date:%d.%m.%Y}: {created} hodim "Kelmadi" deb belgilandi.')
        return redirect('ceo:attendance_list')


class AttendanceStatsView(CEORequiredMixin, View):
    """To'liq davomat statistikasi — effective_shift + multi-shift support."""

    def get(self, request):
        branch = self.get_branch()
        now = timezone.localtime()
        today = now.date()

        period = request.GET.get('period', 'today')
        custom_from = request.GET.get('from_date')
        custom_to = request.GET.get('to_date')

        if period == 'today':
            date_from = date_to = today
            period_label = 'Bugun'
        elif period == 'week':
            date_from = today - datetime.timedelta(days=today.weekday())
            date_to = today
            period_label = 'Shu hafta'
        elif period == 'month':
            date_from = today.replace(day=1)
            date_to = today
            period_label = 'Shu oy'
        elif period == 'custom' and custom_from and custom_to:
            try:
                date_from = datetime.date.fromisoformat(custom_from)
                date_to = datetime.date.fromisoformat(custom_to)
            except ValueError:
                date_from = date_to = today
            period_label = f'{date_from:%d.%m.%Y} — {date_to:%d.%m.%Y}'
        else:
            date_from = date_to = today
            period_label = 'Bugun'

        qs = Attendance.objects.filter(date__gte=date_from, date__lte=date_to)
        if branch:
            qs = qs.filter(branch=branch)

        total_employees = User.objects.filter(branch=branch, is_active=True).count() if branch else 0
        total_days = (date_to - date_from).days + 1

        # === ASOSIY STATISTIKA ===
        total_records = qs.count()
        present_count = qs.filter(status='present').count()
        late_count = qs.filter(status='late').count()
        absent_count = qs.filter(status='absent').count()
        active_now = qs.filter(date=today, check_in__isnull=False, check_out__isnull=True).count()

        checked_in = qs.filter(check_in__isnull=False).count()
        checked_out = qs.filter(check_out__isnull=False).count()
        not_checked_out = qs.filter(check_in__isnull=False, check_out__isnull=True).count()

        expected_total = total_employees * total_days
        # Davomat darajasi: kelgan (present+late) / kutilgan jami
        attendance_rate = round(((present_count + late_count) / expected_total * 100) if expected_total else 0)
        # Aniqlik: o'z vaqtida kelgan / jami kelganlar (late+present)
        punctuality_rate = round((present_count / (present_count + late_count) * 100) if (present_count + late_count) else 0)

        # === ISHLAGAN SOATLAR ===
        worked_records = qs.filter(check_in__isnull=False, check_out__isnull=False)
        total_worked_seconds = 0
        for att in worked_records:
            delta = att.check_out - att.check_in
            total_worked_seconds += max(delta.total_seconds(), 0)

        total_hours = int(total_worked_seconds // 3600)
        total_minutes = int((total_worked_seconds % 3600) // 60)
        avg_hours_per_day = round(total_worked_seconds / 3600 / max(total_records, 1), 1)

        # === SMENA BO'YICHA (effective_shift asosida) ===
        shifts_qs = Shift.objects.filter(branch=branch) if branch else Shift.objects.none()
        shift_stats = []
        for shift in shifts_qs:
            # effective_shift: hodim qaysi smenaga kelganligi (asosiy smena emas, haqiqiy)
            eff_qs = qs.filter(effective_shift=shift)
            # asosiy smena bo'yicha ham (effective_shift null bo'lsa)
            assigned_qs = qs.filter(effective_shift__isnull=True, user__shift=shift)
            combined_qs = qs.filter(
                Q(effective_shift=shift) | Q(effective_shift__isnull=True, user__shift=shift)
            )
            s_total = combined_qs.count()
            s_present = combined_qs.filter(status='present').count()
            s_late = combined_qs.filter(status='late').count()
            s_absent = combined_qs.filter(status='absent').count()
            s_active = combined_qs.filter(date=today, check_in__isnull=False, check_out__isnull=True).count()
            # Boshqa smenadan kelganlar (cross-shift)
            cross_shift = eff_qs.exclude(user__shift=shift).count()
            shift_stats.append({
                'shift': shift,
                'total': s_total,
                'present': s_present,
                'late': s_late,
                'absent': s_absent,
                'active_now': s_active,
                'cross_shift': cross_shift,
                'rate': round(((s_present + s_late) / (s_present + s_late + s_absent) * 100) if (s_present + s_late + s_absent) else 0),
                'punctuality': round((s_present / (s_present + s_late) * 100) if (s_present + s_late) else 0),
            })

        # === BO'LIM BO'YICHA ===
        dept_stats = []
        depts_qs = Department.objects.filter(branch=branch) if branch else Department.objects.none()
        for dept in depts_qs:
            dept_qs = qs.filter(user__department=dept)
            d_total = dept_qs.count()
            d_present = dept_qs.filter(status='present').count()
            d_late = dept_qs.filter(status='late').count()
            d_absent = dept_qs.filter(status='absent').count()
            d_employees = User.objects.filter(branch=branch, department=dept, is_active=True).count()
            dept_stats.append({
                'dept': dept,
                'total': d_total,
                'present': d_present,
                'late': d_late,
                'absent': d_absent,
                'employees': d_employees,
                'rate': round(((d_present + d_late) / (d_employees * total_days) * 100) if d_employees * total_days else 0),
            })

        # === KUNLIK TREND (oxirgi 14 kun yoki tanlangan davr) ===
        trend_days = min(14, total_days)
        daily_trend = []
        for i in range(trend_days - 1, -1, -1):
            d = date_to - datetime.timedelta(days=i)
            if d < date_from:
                continue
            d_qs = qs.filter(date=d)
            d_present = d_qs.filter(status='present').count()
            d_late = d_qs.filter(status='late').count()
            d_absent = d_qs.filter(status='absent').count()
            d_total = d_present + d_late + d_absent
            day_names = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']
            daily_trend.append({
                'date': d.isoformat(),
                'day_name': day_names[d.weekday()],
                'total': d_total,
                'present': d_present,
                'late': d_late,
                'absent': d_absent,
                'is_today': d == today,
            })

        max_daily = max((d['total'] for d in daily_trend), default=1) or 1

        # === SOATLIK TAQSIMOT (bugun uchun) ===
        hourly_dist = []
        if period == 'today':
            hour_qs = qs.filter(check_in__isnull=False)
            hour_counts = defaultdict(int)
            for att in hour_qs:
                h = timezone.localtime(att.check_in).hour
                hour_counts[h] += 1
            for h in range(6, 23):
                hourly_dist.append({'hour': h, 'count': hour_counts.get(h, 0)})

        # === TOP KECHIKUVCHILAR ===
        top_late = (
            qs.filter(status='late')
            .values('user__name', 'user__pk')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )

        top_absent = (
            qs.filter(status='absent')
            .values('user__name', 'user__pk')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )

        # === HEATMAP DATA (oxirgi 90 kun) ===
        heatmap_start = today - datetime.timedelta(days=89)
        heatmap_qs = Attendance.objects.filter(date__gte=heatmap_start, date__lte=today)
        if branch:
            heatmap_qs = heatmap_qs.filter(branch=branch)
        heatmap_counts = dict(
            heatmap_qs.values('date').annotate(cnt=Count('id')).values_list('date', 'cnt')
        )
        heatmap_absent = dict(
            heatmap_qs.filter(status='absent').values('date').annotate(cnt=Count('id')).values_list('date', 'cnt')
        )
        heatmap_data = []
        for i in range(90):
            d = heatmap_start + datetime.timedelta(days=i)
            cnt = heatmap_counts.get(d, 0)
            ab = heatmap_absent.get(d, 0)
            heatmap_data.append({
                'date': d.strftime('%d.%m.%Y'),
                'iso': d.isoformat(),
                'count': cnt,
                'absent': ab,
                'present': cnt - ab,
                'weekday': d.weekday(),
            })

        # === HAFTALIK SOLISHTIRMA ===
        week_compare = []
        for w in range(4):
            w_end = today - datetime.timedelta(days=w * 7)
            w_start = w_end - datetime.timedelta(days=6)
            w_qs = Attendance.objects.filter(date__gte=w_start, date__lte=w_end)
            if branch:
                w_qs = w_qs.filter(branch=branch)
            w_total = w_qs.count()
            w_present = w_qs.filter(status='present').count()
            w_late = w_qs.filter(status='late').count()
            w_absent = w_qs.filter(status='absent').count()
            w_came = w_present + w_late
            week_compare.append({
                'label': f'{w_start:%d.%m}–{w_end:%d.%m}',
                'total': w_total,
                'present': w_present,
                'rate': round((w_came / (w_came + w_absent) * 100) if (w_came + w_absent) else 0),
            })
        week_compare.reverse()

        context = {
            'active_nav': 'stats',
            'branch': branch,
            'period': period,
            'period_label': period_label,
            'from_date': date_from.isoformat(),
            'to_date': date_to.isoformat(),
            'today': today,
            'total_records': total_records,
            'present_count': present_count,
            'late_count': late_count,
            'absent_count': absent_count,
            'active_now': active_now,
            'checked_in': checked_in,
            'checked_out': checked_out,
            'not_checked_out': not_checked_out,
            'total_employees': total_employees,
            'expected_total': expected_total,
            'attendance_rate': attendance_rate,
            'punctuality_rate': punctuality_rate,
            'total_hours': total_hours,
            'total_minutes': total_minutes,
            'avg_hours_per_day': avg_hours_per_day,
            'heatmap_data': heatmap_data,
            'shift_stats': shift_stats,
            'dept_stats': dept_stats,
            'daily_trend': daily_trend,
            'max_daily': max_daily,
            'hourly_dist': hourly_dist,
            'top_late': top_late,
            'top_absent': top_absent,
            'week_compare': week_compare,
        }
        return render(request, 'ceo/attendance_stats.html', context)


# ── Per-Shift Detail ──

class ShiftStatsDetailView(CEORequiredMixin, View):
    """Bitta smena bo'yicha batafsil davomat statistikasi."""

    def get(self, request, pk):
        branch = self.get_branch()
        shift = get_object_or_404(Shift, pk=pk)
        now = timezone.localtime()
        today = now.date()

        period = request.GET.get('period', 'month')
        date_from, date_to, period_label = self._parse_period(period, today, request)

        qs = Attendance.objects.filter(user__shift=shift, date__gte=date_from, date__lte=date_to)
        if branch:
            qs = qs.filter(branch=branch)

        total_days = (date_to - date_from).days + 1
        employees = User.objects.filter(branch=branch, shift=shift, is_active=True) if branch else User.objects.none()
        total_emp = employees.count()

        total = qs.count()
        present = qs.filter(status='present').count()
        late = qs.filter(status='late').count()
        absent = qs.filter(status='absent').count()
        active = qs.filter(date=today, check_in__isnull=False, check_out__isnull=True).count()

        # Hodimlar bo'yicha
        emp_stats = []
        for u in employees:
            u_qs = qs.filter(user=u)
            u_total = u_qs.count()
            u_present = u_qs.filter(status='present').count()
            u_late = u_qs.filter(status='late').count()
            u_absent = u_qs.filter(status='absent').count()
            emp_stats.append({
                'user': u,
                'total': u_total,
                'present': u_present,
                'late': u_late,
                'absent': u_absent,
                'rate': round((u_present / u_total * 100) if u_total else 0),
            })
        emp_stats.sort(key=lambda x: x['rate'], reverse=True)

        # Kunlik trend
        daily = []
        for i in range(min(13, total_days - 1), -1, -1):
            d = today - datetime.timedelta(days=i)
            if d < date_from:
                continue
            d_qs = qs.filter(date=d)
            daily.append({
                'date': d, 'day_name': d.strftime('%A')[:3],
                'total': d_qs.count(),
                'present': d_qs.filter(status='present').count(),
                'late': d_qs.filter(status='late').count(),
                'absent': d_qs.filter(status='absent').count(),
            })
        max_daily = max((d['total'] for d in daily), default=1) or 1

        context = {
            'active_nav': 'stats', 'branch': branch, 'shift': shift,
            'period': period, 'period_label': period_label,
            'from_date': date_from.isoformat(), 'to_date': date_to.isoformat(),
            'total': total, 'present': present, 'late': late,
            'absent': absent, 'active_now': active,
            'total_emp': total_emp,
            'rate': round((present / total * 100) if total else 0),
            'emp_stats': emp_stats, 'daily': daily, 'max_daily': max_daily,
        }
        return render(request, 'ceo/shift_stats_detail.html', context)

    def _parse_period(self, period, today, request):
        if period == 'today':
            return today, today, 'Bugun'
        elif period == 'week':
            return today - datetime.timedelta(days=today.weekday()), today, 'Shu hafta'
        elif period == 'month':
            return today.replace(day=1), today, 'Shu oy'
        elif period == 'custom':
            try:
                f = datetime.date.fromisoformat(request.GET.get('from_date', ''))
                t = datetime.date.fromisoformat(request.GET.get('to_date', ''))
                return f, t, f'{f:%d.%m.%Y} — {t:%d.%m.%Y}'
            except ValueError:
                pass
        return today, today, 'Bugun'


# ── Per-Department Detail ──

class DeptStatsDetailView(CEORequiredMixin, View):
    """Bitta bo'lim bo'yicha batafsil davomat statistikasi."""

    def get(self, request, pk):
        branch = self.get_branch()
        dept = get_object_or_404(Department, pk=pk)
        now = timezone.localtime()
        today = now.date()

        period = request.GET.get('period', 'month')
        date_from, date_to, period_label = ShiftStatsDetailView._parse_period(None, period, today, request)

        qs = Attendance.objects.filter(user__department=dept, date__gte=date_from, date__lte=date_to)
        if branch:
            qs = qs.filter(branch=branch)

        total_days = (date_to - date_from).days + 1
        employees = User.objects.filter(branch=branch, department=dept, is_active=True) if branch else User.objects.none()
        total_emp = employees.count()

        total = qs.count()
        present = qs.filter(status='present').count()
        late = qs.filter(status='late').count()
        absent = qs.filter(status='absent').count()
        active = qs.filter(date=today, check_in__isnull=False, check_out__isnull=True).count()

        # Hodimlar
        emp_stats = []
        for u in employees:
            u_qs = qs.filter(user=u)
            u_total = u_qs.count()
            u_present = u_qs.filter(status='present').count()
            u_late = u_qs.filter(status='late').count()
            u_absent = u_qs.filter(status='absent').count()
            emp_stats.append({
                'user': u, 'total': u_total,
                'present': u_present, 'late': u_late, 'absent': u_absent,
                'rate': round((u_present / u_total * 100) if u_total else 0),
            })
        emp_stats.sort(key=lambda x: x['rate'], reverse=True)

        # Smena bo'yicha
        shift_breakdown = []
        shifts_qs = Shift.objects.filter(branch=branch) if branch else Shift.objects.none()
        for s in shifts_qs:
            s_qs = qs.filter(user__shift=s)
            s_total = s_qs.count()
            if s_total:
                shift_breakdown.append({
                    'shift': s, 'total': s_total,
                    'present': s_qs.filter(status='present').count(),
                    'late': s_qs.filter(status='late').count(),
                    'absent': s_qs.filter(status='absent').count(),
                })

        # Kunlik trend
        daily = []
        for i in range(min(13, total_days - 1), -1, -1):
            d = today - datetime.timedelta(days=i)
            if d < date_from:
                continue
            d_qs = qs.filter(date=d)
            daily.append({
                'date': d, 'day_name': d.strftime('%A')[:3],
                'total': d_qs.count(),
                'present': d_qs.filter(status='present').count(),
                'late': d_qs.filter(status='late').count(),
                'absent': d_qs.filter(status='absent').count(),
            })
        max_daily = max((d['total'] for d in daily), default=1) or 1

        context = {
            'active_nav': 'stats', 'branch': branch, 'dept': dept,
            'period': period, 'period_label': period_label,
            'from_date': date_from.isoformat(), 'to_date': date_to.isoformat(),
            'total': total, 'present': present, 'late': late,
            'absent': absent, 'active_now': active,
            'total_emp': total_emp,
            'rate': round((present / total * 100) if total else 0),
            'emp_stats': emp_stats, 'shift_breakdown': shift_breakdown,
            'daily': daily, 'max_daily': max_daily,
        }
        return render(request, 'ceo/dept_stats_detail.html', context)


# ── Per-Person Detail ──

class UserStatsDetailView(CEORequiredMixin, View):
    """Bitta hodim bo'yicha batafsil davomat statistikasi."""

    def get(self, request, pk):
        branch = self.get_branch()
        user_qs = User.objects.all()
        if branch:
            user_qs = user_qs.filter(branch=branch)
        employee = get_object_or_404(user_qs.select_related('role', 'department', 'shift'), pk=pk)

        now = timezone.localtime()
        today = now.date()

        period = request.GET.get('period', 'month')
        date_from, date_to, period_label = ShiftStatsDetailView._parse_period(None, period, today, request)

        qs = Attendance.objects.filter(user=employee, date__gte=date_from, date__lte=date_to)
        if branch:
            qs = qs.filter(branch=branch)

        total_days = (date_to - date_from).days + 1
        total = qs.count()
        present = qs.filter(status='present').count()
        late = qs.filter(status='late').count()
        absent = qs.filter(status='absent').count()

        # Ishlagan soatlar
        worked = qs.filter(check_in__isnull=False, check_out__isnull=False)
        total_seconds = 0
        for att in worked:
            total_seconds += (att.check_out - att.check_in).total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        avg_per_day = round(total_seconds / 3600 / max(total, 1), 1)

        # Kunlik jadval
        daily_records = qs.select_related('user__shift').order_by('-date', '-check_in')[:30]

        # Kunlik trend
        daily = []
        for i in range(min(13, total_days - 1), -1, -1):
            d = today - datetime.timedelta(days=i)
            if d < date_from:
                continue
            d_qs = qs.filter(date=d)
            daily.append({
                'date': d, 'day_name': d.strftime('%A')[:3],
                'total': d_qs.count(),
                'present': d_qs.filter(status='present').count(),
                'late': d_qs.filter(status='late').count(),
                'absent': d_qs.filter(status='absent').count(),
            })
        max_daily = max((d['total'] for d in daily), default=1) or 1

        # Heatmap (90 kun)
        heatmap_start = today - datetime.timedelta(days=89)
        h_qs = Attendance.objects.filter(user=employee, date__gte=heatmap_start, date__lte=today)
        if branch:
            h_qs = h_qs.filter(branch=branch)
        h_counts = dict(h_qs.values('date').annotate(cnt=Count('id')).values_list('date', 'cnt'))
        h_absent = dict(h_qs.filter(status='absent').values('date').annotate(cnt=Count('id')).values_list('date', 'cnt'))
        heatmap_data = []
        for i in range(90):
            d = heatmap_start + datetime.timedelta(days=i)
            heatmap_data.append({
                'date': d.isoformat(), 'count': h_counts.get(d, 0),
                'absent': h_absent.get(d, 0), 'weekday': d.weekday(),
            })

        context = {
            'active_nav': 'stats', 'branch': branch, 'employee': employee,
            'period': period, 'period_label': period_label,
            'from_date': date_from.isoformat(), 'to_date': date_to.isoformat(),
            'total': total, 'present': present, 'late': late,
            'absent': absent,
            'rate': round((present / total * 100) if total else 0),
            'hours': hours, 'minutes': minutes, 'avg_per_day': avg_per_day,
            'daily_records': daily_records,
            'daily': daily, 'max_daily': max_daily,
            'heatmap_data': heatmap_data,
        }
        return render(request, 'ceo/user_stats_detail.html', context)


class QRCardView(CEORequiredMixin, View):
    """Hodimning QR kodi sahifasi — print qilish uchun."""

    def get(self, request, pk):
        branch = self.get_branch()
        qs = User.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        user = get_object_or_404(qs, pk=pk)
        return render(request, 'ceo/qr_card.html', {
            'active_nav': 'users',
            'employee': user,
            'qr_token': generate_qr_token(user),
        })


class QRCardAllView(CEORequiredMixin, View):
    """Barcha hodimlarning QR kodlari — print uchun, filter bilan."""

    def get(self, request):
        branch = self.get_branch()
        if branch:
            users = User.objects.filter(branch=branch, is_active=True).select_related('role', 'department', 'shift')
        else:
            users = User.objects.none()

        # Filters
        dept_filter = request.GET.get('department', '')
        shift_filter = request.GET.get('shift', '')
        search = request.GET.get('q', '').strip()

        if dept_filter:
            users = users.filter(department_id=dept_filter)
        if shift_filter:
            users = users.filter(shift_id=shift_filter)
        if search:
            users = users.filter(name__icontains=search)

        user_cards = [{'user': u, 'token': generate_qr_token(u)} for u in users]

        departments = Department.objects.filter(branch=branch) if branch else Department.objects.none()
        shifts = Shift.objects.filter(branch=branch) if branch else Shift.objects.none()

        return render(request, 'ceo/qr_cards_all.html', {
            'active_nav': 'qr_cards',
            'user_cards': user_cards,
            'branch': branch,
            'departments': departments,
            'shifts': shifts,
            'filter_dept': dept_filter,
            'filter_shift': shift_filter,
            'filter_search': search,
        })


# ══════════════════════════════════════════════════════════════════
# SALARY / OYLIK
# ══════════════════════════════════════════════════════════════════

def _calc_worked_seconds(att):
    """
    Oddiy hodim uchun hisob soatlari (soniyalarda).
    billing_check_in (effective_check_in yoki check_in) → check_out farqi.
    Smena grace period allaqachon check_out ga yozilgan (kiosk tomonidan).
    """
    ci = att.effective_check_in or att.check_in
    co = att.check_out
    if ci and co:
        return max((co - ci).total_seconds(), 0)
    return 0


def _vip_shift_full_seconds(shift, ref_date):
    """
    VIP hodim uchun smena to'liq davomiyligi (sekundda).
    Erta chiqsa ham, kech chiqsa ham — doimo to'liq smena vaqti qaytariladi.
    """
    from apps.attendance.view2 import _shift_start_dt, _shift_end_dt_from_start
    if not shift or not shift.start_time or not shift.end_time:
        return 0
    start_dt = _shift_start_dt(shift, ref_date)
    end_dt = _shift_end_dt_from_start(shift, start_dt)
    if not start_dt or not end_dt:
        return 0
    return max((end_dt - start_dt).total_seconds(), 0)


def _month_salary_for_user(user, year, month, branch):
    """
    Bir hodim uchun bir oylik oylik hisob-kitobi.
    Har bir davomat yozuvi O'SHA KUNDAGI stavka bilan hisoblanadi
    (HourlyRateHistory.rate_for_date), shunda stavka o'zgarishi faqat
    o'sha sanadan keyingi yozuvlarga ta'sir qiladi.
    """
    from apps.ceo.models import HourlyRateHistory, SalaryBonus
    from decimal import Decimal
    import calendar

    # Oyning boshlanish/tugash sanasi
    last_day = calendar.monthrange(year, month)[1]
    date_from = datetime.date(year, month, 1)
    date_to   = datetime.date(year, month, last_day)

    # Davomat yozuvlari (faqat shu oyda, shu filialdagi)
    qs = Attendance.objects.filter(
        user=user, date__gte=date_from, date__lte=date_to,
    ).select_related('effective_shift')
    if branch:
        qs = qs.filter(branch=branch)

    # Stavka tarixi: shu oy ichida qo'llaniladigan yozuvlar
    rate_entries = list(
        HourlyRateHistory.objects.filter(user=user, effective_from__lte=date_to)
        .order_by('-effective_from')
    )
    current_rate = rate_entries[0].hourly_rate if rate_entries else Decimal('0.00')

    def _rate_for_date(date):
        for entry in rate_entries:
            if entry.effective_from <= date:
                return entry.hourly_rate
        return Decimal('0.00')

    from apps.users.models import VipStatusHistory

    att_rows = []
    total_seconds = Decimal('0')
    base_salary = Decimal('0.00')

    # VIP tarix yozuvlarini oldindan yuklash (har kun uchun DB ga bormaslik uchun)
    vip_history = list(
        VipStatusHistory.objects.filter(user=user, effective_from__lte=date_to)
        .order_by('-effective_from', '-created_at')
    )
    _vip_cache = {}

    def _is_vip_on(date):
        if date in _vip_cache:
            return _vip_cache[date]
        result = None
        for entry in vip_history:
            if entry.effective_from <= date:
                result = entry.is_vip
                break
        if result is None:
            result = getattr(user, 'is_vip', False)
        _vip_cache[date] = result
        return result

    # VIP: bir kun + bir smena = bitta hisob yozuvi.
    # Bir nechta yozuv bo'lsa — faqat birinchi kirish va oxirgi chiqish hisobga olinadi,
    # lekin billing = smena to'liq vaqti (erta chiqsa ham).
    from collections import defaultdict

    # Guruhlaymiz: (date, shift_id) → [att, ...]
    groups = defaultdict(list)
    for att in qs.order_by('date', 'check_in'):
        shift_key = att.effective_shift_id or 0
        groups[(att.date, shift_key)].append(att)

    for (date, shift_key), group_atts in sorted(groups.items()):
        day_is_vip = _is_vip_on(date)
        rate = _rate_for_date(date)

        # absent-only guruh
        all_absent = all(a.status == 'absent' for a in group_atts)

        if day_is_vip and not all_absent:
            # VIP: to'liq smena vaqti — bitta yozuv yoki bir nechta bo'lsa ham
            # birinchi kelgan attni asosiy sifatida olamiz
            primary = next((a for a in group_atts if a.status != 'absent'), group_atts[0])
            shift = primary.effective_shift
            secs = _vip_shift_full_seconds(shift, date)
            vip_full_shift = True

            hours_dec = Decimal(str(round(secs / 3600, 6)))
            earned = (hours_dec * rate).quantize(Decimal('0.01'))
            base_salary += earned
            total_seconds += Decimal(str(secs))

            # Birinchi yozuv asosiy, qolganlari "duplicate" sifatida 0 earned bilan
            for i, att in enumerate(group_atts):
                if i == 0 or att == primary:
                    att_rows.append({
                        'att':            att,
                        'worked_seconds': float(secs),
                        'worked_hours':   round(float(secs) / 3600, 2),
                        'rate':           rate,
                        'earned':         earned,
                        'vip_full_shift': vip_full_shift,
                        'day_is_vip':     day_is_vip,
                        'is_primary':     True,
                    })
                    # Faqat bir marta hisoblash uchun earned ni keyingi iteratsiyalarda 0 qilamiz
                    earned = Decimal('0.00')
                    secs = 0.0
                else:
                    att_rows.append({
                        'att':            att,
                        'worked_seconds': 0.0,
                        'worked_hours':   0.0,
                        'rate':           rate,
                        'earned':         Decimal('0.00'),
                        'vip_full_shift': False,
                        'day_is_vip':     day_is_vip,
                        'is_primary':     False,
                    })
        else:
            # Oddiy hodim: har bir yozuv alohida hisoblanadi
            for att in group_atts:
                secs = _calc_worked_seconds(att)
                hours_dec = Decimal(str(round(secs / 3600, 6)))
                earned = (hours_dec * rate).quantize(Decimal('0.01'))
                base_salary += earned
                total_seconds += Decimal(str(secs))
                att_rows.append({
                    'att':            att,
                    'worked_seconds': float(secs),
                    'worked_hours':   round(float(secs) / 3600, 2),
                    'rate':           rate,
                    'earned':         earned,
                    'vip_full_shift': False,
                    'day_is_vip':     day_is_vip,
                    'is_primary':     True,
                })

    total_hours = float(total_seconds) / 3600

    # Bonus / KPI / jarima
    bonuses = list(SalaryBonus.objects.filter(user=user, year=year, month=month).order_by('created_at'))
    bonus_total   = sum(b.amount for b in bonuses if not b.is_deduction)
    penalty_total = sum(b.amount for b in bonuses if b.is_deduction)
    net_salary = base_salary + bonus_total - penalty_total

    return {
        'user':          user,
        'current_rate':  current_rate,
        'rate_entries':  rate_entries,
        'att_rows':      att_rows,
        'total_seconds': float(total_seconds),
        'total_hours':   total_hours,
        'base_salary':   base_salary,
        'bonuses':       bonuses,
        'bonus_total':   bonus_total,
        'penalty_total': penalty_total,
        'net_salary':    net_salary,
        'present_count': qs.filter(status='present').count(),
        'late_count':    qs.filter(status='late').count(),
        'absent_count':  qs.filter(status='absent').count(),
        'total_records': qs.count(),
    }


class SalaryListView(CEORequiredMixin, View):
    """Barcha hodimlar uchun oylik ro'yxati."""

    def get(self, request):
        branch = self.get_branch()
        now = timezone.localtime()

        year  = int(request.GET.get('year',  now.year))
        month = int(request.GET.get('month', now.month))

        # Yil/oy tekshiruv
        year  = max(2020, min(year,  2100))
        month = max(1,    min(month, 12))

        users = User.objects.filter(is_active=True).select_related(
            'role', 'department', 'shift',
        )
        if branch:
            users = users.filter(branch=branch)

        # ── Filterlar ──
        filter_dept   = request.GET.get('department', '').strip()
        filter_role   = request.GET.get('role', '').strip()
        filter_status = request.GET.get('status', '').strip()
        filter_vip    = request.GET.get('vip', '').strip()
        filter_search = request.GET.get('search', '').strip()

        if filter_dept:
            users = users.filter(department_id=filter_dept)
        if filter_role:
            users = users.filter(role_id=filter_role)
        if filter_status == 'active':
            users = users.filter(is_active=True)
        elif filter_status == 'inactive':
            users = users.filter(is_active=False)
        if filter_vip == '1':
            users = users.filter(is_vip=True)
        elif filter_vip == '0':
            users = users.filter(is_vip=False)
        if filter_search:
            users = users.filter(name__icontains=filter_search)

        rows = []
        grand_base = grand_net = grand_hours = 0
        for u in users:
            data = _month_salary_for_user(u, year, month, branch)
            rows.append(data)
            grand_base  += float(data['base_salary'])
            grand_net   += float(data['net_salary'])
            grand_hours += data['total_hours']

        # Oy nomi
        month_names = [
            '', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
            'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr',
        ]

        years = list(range(2024, now.year + 2))
        departments = Department.objects.filter(branch=branch) if branch else Department.objects.all()
        roles = Role.objects.all()

        context = {
            'active_nav':    'salary',
            'branch':        branch,
            'year':          year,
            'month':         month,
            'month_name':    month_names[month],
            'rows':          rows,
            'grand_base':    round(grand_base, 2),
            'grand_net':     round(grand_net, 2),
            'grand_hours':   round(grand_hours, 2),
            'month_names':   month_names[1:],
            'years':         years,
            'departments':   departments,
            'roles':         roles,
            'filter_dept':   filter_dept,
            'filter_role':   filter_role,
            'filter_status': filter_status,
            'filter_vip':    filter_vip,
            'filter_search': filter_search,
        }
        return render(request, 'ceo/salary_list.html', context)


class SalaryDetailView(CEORequiredMixin, View):
    """Bitta hodim uchun oylik batafsil."""

    def get(self, request, pk):
        branch = self.get_branch()
        qs = User.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        employee = get_object_or_404(qs.select_related('role', 'department', 'shift'), pk=pk)

        now   = timezone.localtime()
        year  = int(request.GET.get('year',  now.year))
        month = int(request.GET.get('month', now.month))
        year  = max(2020, min(year,  2100))
        month = max(1,    min(month, 12))

        data = _month_salary_for_user(employee, year, month, branch)

        from apps.users.models import VipStatusHistory
        vip_history = list(
            VipStatusHistory.objects.filter(user=employee)
            .order_by('-effective_from', '-created_at')
            .select_related('created_by')[:20]
        )

        month_names = [
            '', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
            'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr',
        ]
        years = list(range(2024, now.year + 2))

        context = {
            'active_nav': 'salary',
            'branch': branch,
            'employee': employee,
            'year': year,
            'month': month,
            'month_name': month_names[month],
            'years': years,
            'month_names': month_names[1:],
            'vip_history': vip_history,
            'today': now.date(),
            **data,
        }
        return render(request, 'ceo/salary_detail.html', context)

    def post(self, request, pk):
        """Soatlik stavka yangilash yoki bonus/jarima qo'shish."""
        from apps.ceo.models import HourlyRateHistory, SalaryBonus
        from decimal import Decimal

        branch = self.get_branch()
        qs = User.objects.all()
        if branch:
            qs = qs.filter(branch=branch)
        employee = get_object_or_404(qs, pk=pk)

        now   = timezone.localtime()
        year  = int(request.POST.get('year',  now.year))
        month = int(request.POST.get('month', now.month))
        action = request.POST.get('action', '')

        if action == 'set_rate':
            try:
                rate = Decimal(request.POST.get('hourly_rate', '0').replace(',', '.'))
                rate = max(Decimal('0'), rate)
            except Exception:
                rate = Decimal('0')
            try:
                eff_from = datetime.date.fromisoformat(request.POST.get('effective_from', ''))
            except ValueError:
                eff_from = timezone.localtime().date()
            # Agar o'sha sanada allaqachon yozuv bo'lsa — yangilaymiz
            obj, created = HourlyRateHistory.objects.get_or_create(
                user=employee, effective_from=eff_from,
                defaults={'hourly_rate': rate},
            )
            if not created:
                obj.hourly_rate = rate
                obj.save()
            note_val = request.POST.get('rate_note', '').strip()[:255]
            if note_val:
                obj.note = note_val
                obj.save(update_fields=['note'])
            messages.success(
                request,
                f'Stavka {rate:,.0f} so\'m/soat — {eff_from.strftime("%d.%m.%Y")} sanadan boshlab.'
            )

        elif action == 'delete_rate':
            rate_id = request.POST.get('rate_id')
            try:
                HourlyRateHistory.objects.filter(pk=rate_id, user=employee).delete()
                messages.success(request, 'Stavka yozuvi o\'chirildi.')
            except Exception:
                pass

        elif action == 'add_bonus':
            try:
                amount = Decimal(request.POST.get('amount', '0').replace(',', '.'))
                amount = max(Decimal('0'), amount)
            except Exception:
                amount = Decimal('0')
            bonus_type = request.POST.get('bonus_type', 'bonus')
            note = request.POST.get('note', '').strip()[:255]
            if amount > 0:
                SalaryBonus.objects.create(
                    user=employee, year=year, month=month,
                    bonus_type=bonus_type, amount=amount, note=note,
                )
                label = 'Jarima' if bonus_type == 'penalty' else 'Bonus/KPI'
                messages.success(request, f'{label} qo\'shildi: {amount:,.0f} so\'m')
            else:
                messages.warning(request, 'Miqdor 0 dan katta bo\'lishi kerak.')

        elif action == 'delete_bonus':
            bonus_id = request.POST.get('bonus_id')
            try:
                SalaryBonus.objects.filter(pk=bonus_id, user=employee).delete()
                messages.success(request, 'O\'chirildi.')
            except Exception:
                pass

        elif action == 'set_vip_status':
            from apps.users.models import VipStatusHistory
            new_vip = request.POST.get('vip_status') == '1'
            try:
                eff_from = datetime.date.fromisoformat(request.POST.get('vip_effective_from', ''))
            except ValueError:
                eff_from = timezone.localtime().date()
            note_vip = request.POST.get('vip_note', '').strip()[:255]
            VipStatusHistory.objects.create(
                user=employee,
                is_vip=new_vip,
                effective_from=eff_from,
                note=note_vip,
                created_by=request.user,
            )
            # User.is_vip ni ham yangilaymiz (joriy holat uchun)
            employee.is_vip = new_vip
            employee.save(update_fields=['is_vip'])
            label = 'berildi' if new_vip else 'olindi'
            messages.success(request, f'VIP status {label} — {eff_from.strftime("%d.%m.%Y")} sanadan.')

        elif action == 'delete_vip_history':
            from apps.users.models import VipStatusHistory
            vid = request.POST.get('vip_id')
            try:
                VipStatusHistory.objects.filter(pk=vid, user=employee).delete()
                messages.success(request, 'VIP yozuvi o\'chirildi.')
                # Oxirgi yozuvga qarab User.is_vip ni yangilaymiz
                last = VipStatusHistory.objects.filter(user=employee).order_by('-effective_from', '-created_at').first()
                employee.is_vip = last.is_vip if last else False
                employee.save(update_fields=['is_vip'])
            except Exception:
                pass

        return redirect(f'{request.path}?year={year}&month={month}')


# ── Quyish loglar (CEO) ──────────────────────────────────────────────────────

from apps.casting.models import (  # noqa: E402
    AdditionalHomLog, AdditionalOrder, AdditionalTayorLog,
    HomMahsulotLog, RasxodLog, Stanok, Zamak, QuyishRasxod,
)
from apps.order.models import Order as _Order  # noqa: E402
from django.db.models import Sum as _Sum  # noqa: E402


def _log_ctx(order, user_pk=None):
    qs       = order.hom_loglar.select_related('stanok', 'created_by').order_by('-sana', '-created_at')
    hom_jami = qs.aggregate(j=_Sum('miqdor'))['j'] or 0
    hom_loglar = list(qs)
    for log in hom_loglar:
        log.is_mine = (user_pk is not None and log.created_by_id == user_pk)
    return {
        'hom_loglar': hom_loglar,
        'hom_jami':   hom_jami,
        'stanoklar':  Stanok.objects.filter(status=Stanok.Status.ACTIVE),
        'today':      timezone.localdate(),
    }


class OrderLogView(CEORequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(_Order.objects.select_related('brujka', 'created_by'), pk=pk)
        return render(request, 'ceo/order_log.html', {
            'order': order, 'active_nav': 'orders',
            **_log_ctx(order, user_pk=request.user.pk),
        })


class HomLogCreateView(CEORequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(_Order, pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('ceo:order_log', pk=pk)
        import datetime as _dt
        try:
            sana = _dt.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = timezone.localdate()
        stanok_id = request.POST.get('stanok', '').strip()
        stanok = Stanok.objects.filter(pk=stanok_id).first() if stanok_id else None
        smena = request.POST.get('smena', HomMahsulotLog.Smena.KUN)
        if smena not in dict(HomMahsulotLog.Smena.choices):
            smena = HomMahsulotLog.Smena.KUN
        HomMahsulotLog.objects.create(
            order=order, stanok=stanok, miqdor=miqdor, smena=smena, sana=sana,
            izoh=request.POST.get('izoh', '').strip(), created_by=request.user,
        )
        messages.success(request, f'{miqdor} dona hom mahsulot qo\'shildi ({smena} smenasi).')
        return redirect('ceo:order_log', pk=pk)


class HomLogEditView(CEORequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(HomMahsulotLog, pk=log_pk, order_id=pk)
        if log.created_by_id != request.user.pk:
            messages.error(request, 'Faqat o\'zingiz kiritgan logni tahrirlashingiz mumkin.')
            return redirect('ceo:order_log', pk=pk)
        import datetime as _dt
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('ceo:order_log', pk=pk)
        try:
            sana = _dt.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = log.sana
        stanok_id = request.POST.get('stanok', '').strip()
        smena = request.POST.get('smena', log.smena)
        if smena not in dict(HomMahsulotLog.Smena.choices):
            smena = log.smena
        log.stanok = Stanok.objects.filter(pk=stanok_id).first() if stanok_id else None
        log.miqdor = miqdor
        log.smena  = smena
        log.sana   = sana
        log.izoh   = request.POST.get('izoh', '').strip()
        log.save()
        messages.success(request, 'Log yangilandi.')
        return redirect('ceo:order_log', pk=pk)


class HomLogDeleteView(CEORequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(HomMahsulotLog, pk=log_pk, order_id=pk)
        if log.created_by_id != request.user.pk:
            messages.error(request, 'Faqat o\'zingiz kiritgan logni o\'chirishingiz mumkin.')
            return redirect('ceo:order_log', pk=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('ceo:order_log', pk=pk)


# ── Stanoklar ────────────────────────────────────────────────────────────────


class StanokListView(CEORequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        status_f = request.GET.get('status', '')
        qs = Stanok.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)
        if status_f:
            qs = qs.filter(status=status_f)
        counts = {
            'total':    Stanok.objects.count(),
            'active':   Stanok.objects.filter(status=Stanok.Status.ACTIVE).count(),
            'repair':   Stanok.objects.filter(status=Stanok.Status.REPAIR).count(),
            'inactive': Stanok.objects.filter(status=Stanok.Status.INACTIVE).count(),
        }
        return render(request, 'ceo/stanok_list.html', {
            'stanoklar': qs,
            'q': q,
            'status_f': status_f,
            'counts': counts,
            'statuses': Stanok.Status.choices,
            'active_nav': 'stanoklar',
        })


class StanokCreateView(CEORequiredMixin, View):
    def get(self, request):
        return render(request, 'ceo/stanok_form.html', {
            'title': 'Yangi stanok',
            'statuses': Stanok.Status.choices,
            'active_nav': 'stanoklar',
        })

    def post(self, request):
        name   = request.POST.get('name', '').strip()
        status = request.POST.get('status', Stanok.Status.ACTIVE)
        errors = {}
        if not name:
            errors['name'] = 'Nomi majburiy.'
        if status not in dict(Stanok.Status.choices):
            errors['status'] = "Noto'g'ri holat."
        if errors:
            return render(request, 'ceo/stanok_form.html', {
                'title': 'Yangi stanok', 'statuses': Stanok.Status.choices,
                'errors': errors, 'data': request.POST, 'active_nav': 'stanoklar',
            })
        s = Stanok.objects.create(name=name, status=status)
        messages.success(request, f'"{s.name}" stanogi qo\'shildi.')
        return redirect('ceo:stanok_list')


class StanokUpdateView(CEORequiredMixin, View):
    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        return render(request, 'ceo/stanok_form.html', {
            'title': f'{stanok.name} — tahrirlash',
            'stanok': stanok,
            'statuses': Stanok.Status.choices,
            'active_nav': 'stanoklar',
        })

    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        name   = request.POST.get('name', '').strip()
        status = request.POST.get('status', stanok.status)
        errors = {}
        if not name:
            errors['name'] = 'Nomi majburiy.'
        if status not in dict(Stanok.Status.choices):
            errors['status'] = "Noto'g'ri holat."
        if errors:
            return render(request, 'ceo/stanok_form.html', {
                'title': f'{stanok.name} — tahrirlash', 'stanok': stanok,
                'statuses': Stanok.Status.choices, 'errors': errors,
                'data': request.POST, 'active_nav': 'stanoklar',
            })
        stanok.name = name
        stanok.status = status
        stanok.save()
        messages.success(request, f'"{stanok.name}" yangilandi.')
        return redirect('ceo:stanok_list')


class StanokDeleteView(CEORequiredMixin, View):
    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        return render(request, 'ceo/stanok_confirm_delete.html', {
            'object': stanok, 'active_nav': 'stanoklar',
        })

    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        name = stanok.name
        stanok.delete()
        messages.success(request, f'"{name}" o\'chirildi.')
        return redirect('ceo:stanok_list')


# ── CEO: Additional Orders ────────────────────────────────────────────────────
import datetime as _ceo_dt  # noqa: E402


class CeoAdditionalOrderListView(CEORequiredMixin, View):
    def get(self, request):
        status_f = request.GET.get('status', '')
        qs = AdditionalOrder.objects.select_related('created_by').annotate(hom_sum=_Sum('hom_loglar__miqdor'))
        if status_f:
            qs = qs.filter(status=status_f)
        counts = {s: AdditionalOrder.objects.filter(status=s).count() for s, _ in AdditionalOrder.Status.choices}
        statuses_with_counts = [(v, l, counts.get(v, 0)) for v, l in AdditionalOrder.Status.choices]
        return render(request, 'ceo/additional_order_list.html', {
            'orders': qs.order_by('-created_at'), 'counts': counts, 'status_f': status_f,
            'statuses': AdditionalOrder.Status.choices,
            'statuses_with_counts': statuses_with_counts,
            'active_nav': 'additional',
        })


class CeoAdditionalOrderCreateView(CEORequiredMixin, View):
    def get(self, request):
        return render(request, 'ceo/additional_order_form.html', {
            'title': "Yangi qo'shimcha buyurtma", 'active_nav': 'additional',
            'today': timezone.localdate(),
        })

    def post(self, request):
        name = request.POST.get('name', '').strip()
        errors = {}
        try:
            qty = int(request.POST.get('quantity', 0))
            assert qty > 0
        except (ValueError, AssertionError):
            errors['quantity'] = "Miqdor musbat son bo'lishi kerak."
            qty = 0
        try:
            deadline = _ceo_dt.date.fromisoformat(request.POST.get('deadline', ''))
        except ValueError:
            errors['deadline'] = "Sana noto'g'ri."
            deadline = None
        if not name:
            errors['name'] = 'Nomi majburiy.'
        if errors:
            return render(request, 'ceo/additional_order_form.html', {
                'title': "Yangi qo'shimcha buyurtma", 'errors': errors,
                'data': request.POST, 'active_nav': 'additional', 'today': timezone.localdate(),
            })
        order = AdditionalOrder.objects.create(
            name=name, quantity=qty, deadline=deadline,
            note=request.POST.get('note', '').strip(), created_by=request.user,
        )
        messages.success(request, f'"{order.name}" yaratildi.')
        return redirect('ceo:additional_order_detail', pk=order.pk)


class CeoAdditionalOrderDetailView(CEORequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        hom_loglar = order.hom_loglar.select_related('stanok', 'created_by').order_by('-sana', '-created_at')
        hom_jami   = hom_loglar.aggregate(j=_Sum('miqdor'))['j'] or 0
        return render(request, 'ceo/additional_order_detail.html', {
            'order':     order,
            'hom_loglar': hom_loglar,
            'hom_jami':  hom_jami,
            'stanoklar': Stanok.objects.filter(status=Stanok.Status.ACTIVE),
            'today':     timezone.localdate(), 'active_nav': 'additional',
        })


class CeoAdditionalOrderSetStatusView(CEORequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        ns = request.POST.get('status', '')
        if ns in dict(AdditionalOrder.Status.choices):
            order.status = ns
            order.save(update_fields=['status'])
            messages.success(request, 'Holat yangilandi.')
        return redirect('ceo:additional_order_detail', pk=pk)


class CeoAdditionalOrderDeleteView(CEORequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(AdditionalOrder, pk=pk).delete()
        messages.success(request, "O'chirildi.")
        return redirect('ceo:additional_order_list')


class CeoAdditionalHomLogCreateView(CEORequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        if order.status == AdditionalOrder.Status.NEW:
            messages.error(request, "Avval ishlab chiqarishga o'tkazing.")
            return redirect('ceo:additional_order_detail', pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('ceo:additional_order_detail', pk=pk)
        try:
            sana = _ceo_dt.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = timezone.localdate()
        stanok_id = request.POST.get('stanok', '').strip()
        stanok = Stanok.objects.filter(pk=stanok_id).first() if stanok_id else None
        AdditionalHomLog.objects.create(
            add_order=order, stanok=stanok, miqdor=miqdor, sana=sana,
            izoh=request.POST.get('izoh', '').strip(), created_by=request.user,
        )
        messages.success(request, f'{miqdor} dona hom qo\'shildi.')
        return redirect('ceo:additional_order_detail', pk=pk)


class CeoAdditionalHomLogDeleteView(CEORequiredMixin, View):
    def post(self, request, pk, log_pk):
        get_object_or_404(AdditionalHomLog, pk=log_pk, add_order_id=pk).delete()
        messages.success(request, "Log o'chirildi.")
        return redirect('ceo:additional_order_detail', pk=pk)


class CeoAdditionalTayorLogCreateView(CEORequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        if order.status == AdditionalOrder.Status.NEW:
            messages.error(request, "Avval ishlab chiqarishga o'tkazing.")
            return redirect('ceo:additional_order_detail', pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('ceo:additional_order_detail', pk=pk)
        try:
            sana = _ceo_dt.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = timezone.localdate()
        AdditionalTayorLog.objects.create(
            add_order=order, miqdor=miqdor, sana=sana,
            izoh=request.POST.get('izoh', '').strip(),
            created_by=request.user,
        )
        messages.success(request, f'{miqdor} dona tayor qo\'shildi.')
        return redirect('ceo:additional_order_detail', pk=pk)


class CeoAdditionalTayorLogDeleteView(CEORequiredMixin, View):
    def post(self, request, pk, log_pk):
        get_object_or_404(AdditionalTayorLog, pk=log_pk, add_order_id=pk).delete()
        messages.success(request, "Log o'chirildi.")
        return redirect('ceo:additional_order_detail', pk=pk)


# ── CEO: Rasxod ────────────────────────────────────────────────────────────────

class CeoRasxodListView(CEORequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()
        try:
            date_from = _ceo_dt.date.fromisoformat(request.GET.get('from', ''))
        except ValueError:
            date_from = today - _ceo_dt.timedelta(days=29)
        try:
            date_to = _ceo_dt.date.fromisoformat(request.GET.get('to', ''))
        except ValueError:
            date_to = today
        stanok_f = request.GET.get('stanok', '').strip()
        zamak_f  = request.GET.get('zamak', '').strip()
        qs = RasxodLog.objects.select_related('stanok', 'zamak', 'created_by').filter(sana__range=(date_from, date_to))
        if stanok_f:
            qs = qs.filter(stanok_id=stanok_f)
        if zamak_f:
            qs = qs.filter(zamak_id=zamak_f)
        return render(request, 'ceo/rasxod_list.html', {
            'rasxodlar': qs.order_by('-sana', '-created_at'),
            'stanoklar': Stanok.objects.filter(status=Stanok.Status.ACTIVE),
            'zamaklar': Zamak.objects.filter(is_active=True),
            'stanok_f': stanok_f, 'zamak_f': zamak_f,
            'date_from': date_from, 'date_to': date_to, 'today': today,
            'stanok_stats': list(qs.values('stanok__name').annotate(j=_Sum('miqdor')).order_by('-j')[:6]),
            'zamak_stats': list(qs.values('zamak__name', 'zamak__unit').annotate(j=_Sum('miqdor')).order_by('-j')[:6]),
            'jami': qs.aggregate(j=_Sum('miqdor'))['j'] or 0,
            'active_nav': 'rasxod',
        })


class CeoRasxodCreateView(CEORequiredMixin, View):
    def post(self, request):
        from decimal import Decimal
        stanok_id = request.POST.get('stanok', '').strip()
        zamak_id  = request.POST.get('zamak', '').strip()
        try:
            miqdor = float(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('ceo:rasxod_list')
        try:
            sana = _ceo_dt.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = timezone.localdate()
        stanok = get_object_or_404(Stanok, pk=stanok_id) if stanok_id else None
        zamak  = get_object_or_404(Zamak, pk=zamak_id) if zamak_id else None
        if not stanok or not zamak:
            messages.error(request, 'Stanok va zamak majburiy.')
            return redirect('ceo:rasxod_list')
        RasxodLog.objects.create(
            stanok=stanok, zamak=zamak, miqdor=Decimal(str(miqdor)),
            sana=sana, izoh=request.POST.get('izoh', '').strip(), created_by=request.user,
        )
        messages.success(request, f'{miqdor} {zamak.unit} rasxod yozildi.')
        return redirect('ceo:rasxod_list')


class CeoRasxodDeleteView(CEORequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(RasxodLog, pk=pk).delete()
        messages.success(request, "Rasxod o'chirildi.")
        return redirect('ceo:rasxod_list')


# ── CEO: Quyish Rasxod ─────────────────────────────────────────────────────────

class CeoQuyishRasxodListView(CEORequiredMixin, View):
    def get(self, request):
        rasxodlar   = QuyishRasxod.objects.select_related('created_by').all()
        jami_miqdor = rasxodlar.aggregate(j=_Sum('miqdor'))['j'] or 0
        return render(request, 'ceo/quyish_rasxod_list.html', {
            'rasxodlar':   rasxodlar,
            'jami_miqdor': jami_miqdor,
            'active_nav':  'quyish_rasxod',
            'today':       timezone.localdate(),
        })


class CeoQuyishRasxodCreateView(CEORequiredMixin, View):
    def post(self, request):
        from apps.casting.forms import QuyishRasxodForm
        form = QuyishRasxodForm(request.POST)
        if form.is_valid():
            r = form.save(commit=False)
            r.created_by = request.user
            r.save()
            messages.success(request, 'Rasxod qo\'shildi.')
        else:
            messages.error(request, 'Xatolik: ' + str(form.errors))
        return redirect('ceo:quyish_rasxod_list')


class CeoQuyishRasxodDeleteView(CEORequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(QuyishRasxod, pk=pk).delete()
        messages.success(request, 'Rasxod o\'chirildi.')
        return redirect('ceo:quyish_rasxod_list')


class CeoZamakListView(CEORequiredMixin, View):
    def get(self, request):
        return render(request, 'ceo/zamak_list.html', {'zamaklar': Zamak.objects.all(), 'active_nav': 'rasxod'})

    def post(self, request):
        name = request.POST.get('name', '').strip()
        unit = request.POST.get('unit', 'kg').strip()
        if not name:
            messages.error(request, 'Nomi majburiy.')
            return redirect('ceo:zamak_list')
        Zamak.objects.create(name=name, unit=unit)
        messages.success(request, f'"{name}" zamak qo\'shildi.')
        return redirect('ceo:zamak_list')


class CeoZamakDeleteView(CEORequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Zamak, pk=pk).delete()
        messages.success(request, "O'chirildi.")
        return redirect('ceo:zamak_list')

