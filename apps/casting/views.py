from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.casting.models import Stanok
from apps.order.models import Order
from apps.order.views.mixins import CastingManagerRequiredMixin


# ── Orders ────────────────────────────────────────────────────────────────────

class CastingOrderListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        status_filter = request.GET.get('status', 'accepted')
        q = request.GET.get('q', '').strip()
        if status_filter not in {'accepted', 'in_process', 'ready'}:
            status_filter = 'accepted'
        qs = Order.objects.select_related('brujka', 'created_by').filter(status=status_filter)
        if q:
            qs = qs.filter(name__icontains=q)
        counts = {
            'accepted':   Order.objects.filter(status='accepted').count(),
            'in_process': Order.objects.filter(status='in_process').count(),
            'ready':      Order.objects.filter(status='ready').count(),
        }
        return render(request, 'casting/order_list.html', {
            'orders': qs.order_by('deadline', '-priority'),
            'status_filter': status_filter,
            'q': q,
            'counts': counts,
            'active_nav': 'orders',
        })


class CastingOrderDetailView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order.objects.select_related('brujka', 'created_by'), pk=pk)
        return render(request, 'casting/order_detail.html', {
            'order': order,
            'active_nav': 'orders',
        })


# ── Stanoklar ─────────────────────────────────────────────────────────────────

class StanokListView(CastingManagerRequiredMixin, View):
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
        return render(request, 'casting/stanok_list.html', {
            'stanoklar': qs,
            'q': q,
            'status_f': status_f,
            'counts': counts,
            'statuses': Stanok.Status.choices,
            'active_nav': 'stanoklar',
        })


class StanokCreateView(CastingManagerRequiredMixin, View):
    def get(self, request):
        return render(request, 'casting/stanok_form.html', {
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
            return render(request, 'casting/stanok_form.html', {
                'title': 'Yangi stanok', 'statuses': Stanok.Status.choices,
                'errors': errors, 'data': request.POST, 'active_nav': 'stanoklar',
            })
        stanok = Stanok.objects.create(name=name, status=status)
        messages.success(request, f'"{stanok.name}" stanogi qo\'shildi.')
        return redirect('casting:stanok_list')


class StanokUpdateView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        return render(request, 'casting/stanok_form.html', {
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
            return render(request, 'casting/stanok_form.html', {
                'title': f'{stanok.name} — tahrirlash', 'stanok': stanok,
                'statuses': Stanok.Status.choices, 'errors': errors,
                'data': request.POST, 'active_nav': 'stanoklar',
            })
        stanok.name = name
        stanok.status = status
        stanok.save()
        messages.success(request, f'"{stanok.name}" yangilandi.')
        return redirect('casting:stanok_list')


class StanokDeleteView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        return render(request, 'casting/stanok_confirm_delete.html', {
            'object': stanok, 'active_nav': 'stanoklar',
        })

    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        name = stanok.name
        stanok.delete()
        messages.success(request, f'"{name}" o\'chirildi.')
        return redirect('casting:stanok_list')
