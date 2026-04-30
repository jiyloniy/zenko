from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy


class ShopManagerRequiredMixin(LoginRequiredMixin):
    """CEO va SHOPMANAGER rollari kirishi mumkin."""
    login_url = reverse_lazy('login')
    ALLOWED_ROLES = {'CEO', 'SHOPMANAGER'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        user = request.user
        role_name = user.role.name if getattr(user, 'role', None) else None
        if not (user.is_superuser or role_name in self.ALLOWED_ROLES):
            messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)
