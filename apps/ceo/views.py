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
        if role_name == 'CEO' or user.is_superuser:
            return redirect('ceo:dashboard')
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
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'users'
        ctx['branch'] = self.get_branch()
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
        qs = Attendance.objects.select_related('user', 'user__shift')
        if branch:
            qs = qs.filter(branch=branch)

        # Filters
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
            qs = qs.filter(user__shift_id=shift_filter)

        return qs

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

        # Smena bo'yicha statistika (hodimning smenasi bo'yicha)
        shift_stats = []
        shifts_qs = Shift.objects.filter(branch=branch) if branch else Shift.objects.none()
        for shift in shifts_qs:
            shift_today = today_qs.filter(user__shift=shift)
            shift_stats.append({
                'shift': shift,
                'total': shift_today.count(),
                'present': shift_today.filter(status='present').count(),
                'late': shift_today.filter(status='late').count(),
                'absent': shift_today.filter(status='absent').count(),
            })

        # Total hodimlar soni (bugun kelishi kerak bo'lganlar)
        total_employees = User.objects.filter(branch=branch, is_active=True).count() if branch else 0

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
            # Statistikalar
            'total_today': total_today,
            'present_today': present_today,
            'late_today': late_today,
            'absent_today': absent_today,
            'active_now': active_now,
            'total_employees': total_employees,
            'attendance_rate': round((total_today / total_employees * 100) if total_employees else 0),
            'shift_stats': shift_stats,
        })
        return ctx


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
        """Hodimlar va ularning smena ma'lumotlarini JSON formatda tayyorlash."""
        import json
        users = User.objects.filter(branch=branch, is_active=True).select_related('shift') if branch else User.objects.none()
        data = {}
        for u in users:
            data[str(u.pk)] = {
                'shift_id': u.shift_id or '',
                'shift_start': u.shift.start_time.strftime('%H:%M') if u.shift and u.shift.start_time else '',
                'shift_end': u.shift.end_time.strftime('%H:%M') if u.shift and u.shift.end_time else '',
            }
        return json.dumps(data)


class AttendanceUpdateView(CEORequiredMixin, View):
    """Davomat yozuvini tahrirlash."""

    def get(self, request, pk):
        branch = self.get_branch()
        att = get_object_or_404(Attendance, pk=pk, branch=branch) if branch else get_object_or_404(Attendance, pk=pk)
        form = AttendanceForm(instance=att, branch=branch)
        return render(request, 'ceo/attendance_form.html', {
            'active_nav': 'attendance', 'form': form, 'title': 'Davomatni tahrirlash',
            'edit_mode': True, 'attendance': att,
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

            created = 0
            updated = 0
            for user in users:
                att = Attendance.objects.filter(user=user, date=date, branch=branch).first()
                if att is None:
                    Attendance.objects.create(
                        user=user,
                        branch=branch,
                        date=date,
                        check_in=dt_in,
                        check_out=dt_out,
                    )
                    created += 1
                    continue
                att.check_in = dt_in
                if not checkout_blank:
                    att.check_out = dt_out
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
        attendance_rate = round((total_records / expected_total * 100) if expected_total else 0)
        punctuality_rate = round((present_count / total_records * 100) if total_records else 0)

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
                'rate': round(((s_present + s_late) / s_total * 100) if s_total else 0),
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
                'rate': round((d_total / (d_employees * total_days) * 100) if d_employees * total_days else 0),
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
            week_compare.append({
                'label': f'{w_start:%d.%m}–{w_end:%d.%m}',
                'total': w_total,
                'present': w_present,
                'rate': round((w_present / w_total * 100) if w_total else 0),
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
