from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy


class CEORequiredMixin(LoginRequiredMixin):
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
        return getattr(self.request.user, 'branch', None)


class CastingManagerRequiredMixin(LoginRequiredMixin):
    """CEO va CASTINGMANAGER rollari kirishi mumkin."""
    login_url = reverse_lazy('login')
    ALLOWED_ROLES = {'CEO', 'CASTINGMANAGER'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        user = request.user
        role_name = user.role.name if getattr(user, 'role', None) else None  # type: ignore[union-attr]
        if not (user.is_superuser or role_name in self.ALLOWED_ROLES):
            messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_branch(self):
        return getattr(self.request.user, 'branch', None)  # type: ignore[union-attr]


class AttachManagerRequiredMixin(LoginRequiredMixin):
    """CEO va ATTACHMANAGER rollari kirishi mumkin."""
    login_url = reverse_lazy('login')
    ALLOWED_ROLES = {'CEO', 'ATTACHMANAGER'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        user = request.user
        role_name = user.role.name if getattr(user, 'role', None) else None  # type: ignore[union-attr]
        if not (user.is_superuser or role_name in self.ALLOWED_ROLES):
            messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_branch(self):
        return getattr(self.request.user, 'branch', None)  # type: ignore[union-attr]
