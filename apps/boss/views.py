from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, TemplateView

from apps.boss.forms import (
    BranchDepartmentForm,
    BranchForm,
    BranchShiftForm,
    BranchUserCreateForm,
    BranchUserUpdateForm,
)
from apps.users.models import Branch, Department, Role, Shift, User


class BOSSRequiredMixin(LoginRequiredMixin):
    """Faqat BOSS rolidagi foydalanuvchiga ruxsat."""
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.role and request.user.role.name == 'BOSS'):
            if not request.user.is_superuser:
                messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
                return redirect('login')
        return super().dispatch(request, *args, **kwargs)


# ── Dashboard ──

class DashboardView(BOSSRequiredMixin, TemplateView):
    template_name = 'boss/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ceo_prefetch = Prefetch(
            'users',
            queryset=User.objects.filter(role__name='CEO'),
            to_attr='ceo_users',
        )
        ctx.update({
            'active_nav': 'dashboard',
            'total_branches': Branch.objects.count(),
            'total_users': User.objects.count(),
            'total_departments': Department.objects.count(),
            'total_shifts': Shift.objects.count(),
            'total_roles': Role.objects.count(),
            'branches': Branch.objects.prefetch_related(ceo_prefetch)[:10],
        })
        return ctx


# ── Branches CRUD ──

class BranchListView(BOSSRequiredMixin, ListView):
    model = Branch
    template_name = 'boss/branch_list.html'
    context_object_name = 'branches'

    def get_queryset(self):
        ceo_prefetch = Prefetch(
            'users',
            queryset=User.objects.filter(role__name='CEO'),
            to_attr='ceo_users',
        )
        return Branch.objects.prefetch_related(ceo_prefetch)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'branches'
        return ctx


class BranchCreateView(BOSSRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = 'boss/branch_form.html'
    success_url = reverse_lazy('boss:branch_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'branches',
            'title': 'Yangi filial',
            'cancel_url': self.success_url,
        })
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Filial muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class BranchUpdateView(BOSSRequiredMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = 'boss/branch_form.html'
    success_url = reverse_lazy('boss:branch_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'branches',
            'title': f'{self.object.name} — tahrirlash',
            'cancel_url': self.success_url,
        })
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Filial muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class BranchDeleteView(BOSSRequiredMixin, DeleteView):
    model = Branch
    template_name = 'boss/confirm_delete.html'
    success_url = reverse_lazy('boss:branch_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'branches', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Filial o\'chirildi.')
        return super().form_valid(form)


# ── Roles CRUD ──

class RoleListView(BOSSRequiredMixin, ListView):
    model = Role
    template_name = 'boss/role_list.html'
    context_object_name = 'roles'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'roles'
        return ctx


class RoleCreateView(BOSSRequiredMixin, CreateView):
    model = Role
    fields = ('name', 'description')
    template_name = 'boss/role_form.html'
    success_url = reverse_lazy('boss:role_list')

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


class RoleUpdateView(BOSSRequiredMixin, UpdateView):
    model = Role
    fields = ('name', 'description')
    template_name = 'boss/role_form.html'
    success_url = reverse_lazy('boss:role_list')

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


class RoleDeleteView(BOSSRequiredMixin, DeleteView):
    model = Role
    template_name = 'boss/confirm_delete.html'
    success_url = reverse_lazy('boss:role_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'roles', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Rol o\'chirildi.')
        return super().form_valid(form)


# ── Departments CRUD ──

class DepartmentListView(BOSSRequiredMixin, ListView):
    model = Department
    template_name = 'boss/department_list.html'
    context_object_name = 'departments'
    queryset = Department.objects.select_related('branch')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'departments'
        return ctx


class DepartmentCreateView(BOSSRequiredMixin, CreateView):
    model = Department
    form_class = BranchDepartmentForm
    template_name = 'boss/department_form.html'
    success_url = reverse_lazy('boss:department_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'departments',
            'title': 'Yangi bo\'lim',
            'cancel_url': self.success_url,
            'branches': Branch.objects.filter(is_active=True),
        })
        return ctx

    def form_valid(self, form):
        branch_id = self.request.POST.get('branch')
        if branch_id:
            form.instance.branch_id = branch_id
        messages.success(self.request, 'Bo\'lim muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class DepartmentUpdateView(BOSSRequiredMixin, UpdateView):
    model = Department
    form_class = BranchDepartmentForm
    template_name = 'boss/department_form.html'
    success_url = reverse_lazy('boss:department_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'departments',
            'title': f'{self.object.name} — tahrirlash',
            'cancel_url': self.success_url,
            'branches': Branch.objects.filter(is_active=True),
        })
        return ctx

    def form_valid(self, form):
        branch_id = self.request.POST.get('branch')
        if branch_id:
            form.instance.branch_id = branch_id
        else:
            form.instance.branch = None
        messages.success(self.request, 'Bo\'lim muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class DepartmentDeleteView(BOSSRequiredMixin, DeleteView):
    model = Department
    template_name = 'boss/confirm_delete.html'
    success_url = reverse_lazy('boss:department_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'departments', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Bo\'lim o\'chirildi.')
        return super().form_valid(form)


# ── Shifts CRUD ──

class ShiftListView(BOSSRequiredMixin, ListView):
    model = Shift
    template_name = 'boss/shift_list.html'
    context_object_name = 'shifts'
    queryset = Shift.objects.select_related('branch')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'shifts'
        return ctx


class ShiftCreateView(BOSSRequiredMixin, CreateView):
    model = Shift
    form_class = BranchShiftForm
    template_name = 'boss/shift_form.html'
    success_url = reverse_lazy('boss:shift_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'shifts',
            'title': 'Yangi smena',
            'cancel_url': self.success_url,
            'branches': Branch.objects.filter(is_active=True),
        })
        return ctx

    def form_valid(self, form):
        branch_id = self.request.POST.get('branch')
        if branch_id:
            form.instance.branch_id = branch_id
        messages.success(self.request, 'Smena muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class ShiftUpdateView(BOSSRequiredMixin, UpdateView):
    model = Shift
    form_class = BranchShiftForm
    template_name = 'boss/shift_form.html'
    success_url = reverse_lazy('boss:shift_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'shifts',
            'title': f'{self.object.name} — tahrirlash',
            'cancel_url': self.success_url,
            'branches': Branch.objects.filter(is_active=True),
        })
        return ctx

    def form_valid(self, form):
        branch_id = self.request.POST.get('branch')
        if branch_id:
            form.instance.branch_id = branch_id
        else:
            form.instance.branch = None
        messages.success(self.request, 'Smena muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class ShiftDeleteView(BOSSRequiredMixin, DeleteView):
    model = Shift
    template_name = 'boss/confirm_delete.html'
    success_url = reverse_lazy('boss:shift_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'shifts', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Smena o\'chirildi.')
        return super().form_valid(form)


# ── Users CRUD ──

class UserListView(BOSSRequiredMixin, ListView):
    model = User
    template_name = 'boss/user_list.html'
    context_object_name = 'users'
    queryset = User.objects.select_related('role', 'department', 'branch', 'shift')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'users'
        return ctx


class UserCreateView(BOSSRequiredMixin, CreateView):
    model = User
    form_class = BranchUserCreateForm
    template_name = 'boss/user_form.html'
    success_url = reverse_lazy('boss:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'users',
            'title': 'Yangi hodim',
            'roles': Role.objects.all(),
            'departments': Department.objects.select_related('branch'),
            'shifts': Shift.objects.select_related('branch'),
            'branches': Branch.objects.filter(is_active=True),
        })
        return ctx

    def form_valid(self, form):
        branch_id = self.request.POST.get('branch')
        if branch_id:
            form.instance.branch_id = branch_id
        messages.success(self.request, 'Hodim muvaffaqiyatli qo\'shildi.')
        return super().form_valid(form)


class UserUpdateView(BOSSRequiredMixin, UpdateView):
    model = User
    form_class = BranchUserUpdateForm
    template_name = 'boss/user_form.html'
    success_url = reverse_lazy('boss:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'active_nav': 'users',
            'title': f'{self.object.name} — tahrirlash',
            'roles': Role.objects.all(),
            'departments': Department.objects.select_related('branch'),
            'shifts': Shift.objects.select_related('branch'),
            'branches': Branch.objects.filter(is_active=True),
        })
        return ctx

    def form_valid(self, form):
        branch_id = self.request.POST.get('branch')
        if branch_id:
            form.instance.branch_id = branch_id
        else:
            form.instance.branch = None
        messages.success(self.request, 'Hodim muvaffaqiyatli yangilandi.')
        return super().form_valid(form)


class UserDeleteView(BOSSRequiredMixin, DeleteView):
    model = User
    template_name = 'boss/confirm_delete.html'
    success_url = reverse_lazy('boss:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'active_nav': 'users', 'cancel_url': self.success_url})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Hodim o\'chirildi.')
        return super().form_valid(form)
