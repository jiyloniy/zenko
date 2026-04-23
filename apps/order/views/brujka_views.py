from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, ListView

from apps.order.models import Brujka
from apps.order.forms import BrujkaForm
from apps.order.views.mixins import CEORequiredMixin


class BrujkaListView(CEORequiredMixin, ListView):
    model = Brujka
    template_name = 'order/brujka_list.html'
    context_object_name = 'brujkalar'

    def get_queryset(self):
        qs = Brujka.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'brujka'
        ctx['q'] = self.request.GET.get('q', '')
        ctx['total'] = Brujka.objects.count()
        ctx['active_count'] = Brujka.objects.filter(is_active=True).count()
        return ctx


class BrujkaCreateView(CEORequiredMixin, View):
    template_name = 'order/brujka_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': BrujkaForm(),
            'title': 'Yangi brujka',
            'active_nav': 'brujka',
        })

    def post(self, request):
        form = BrujkaForm(request.POST, request.FILES)
        if form.is_valid():
            brujka = form.save()
            messages.success(request, f'"{brujka.name}" brujkasi yaratildi.')
            return redirect('order:broshka_detail', pk=brujka.pk)
        return render(request, self.template_name, {
            'form': form,
            'title': 'Yangi brujka',
            'active_nav': 'brujka',
        })


class BrujkaDetailView(CEORequiredMixin, View):
    template_name = 'order/brujka_detail.html'

    def get(self, request, pk):
        brujka = get_object_or_404(Brujka, pk=pk)
        orders = brujka.orders.select_related('created_by').order_by('-created_at')[:10]
        return render(request, self.template_name, {
            'brujka': brujka,
            'orders': orders,
            'active_nav': 'brujka',
        })


class BrujkaUpdateView(CEORequiredMixin, View):
    template_name = 'order/brujka_form.html'

    def get(self, request, pk):
        brujka = get_object_or_404(Brujka, pk=pk)
        return render(request, self.template_name, {
            'form': BrujkaForm(instance=brujka),
            'brujka': brujka,
            'title': f'{brujka.name} — tahrirlash',
            'active_nav': 'brujka',
        })

    def post(self, request, pk):
        brujka = get_object_or_404(Brujka, pk=pk)
        form = BrujkaForm(request.POST, request.FILES, instance=brujka)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{brujka.name}" yangilandi.')
            return redirect('order:broshka_detail', pk=brujka.pk)
        return render(request, self.template_name, {
            'form': form,
            'brujka': brujka,
            'title': f'{brujka.name} — tahrirlash',
            'active_nav': 'brujka',
        })


class BrujkaDeleteView(CEORequiredMixin, DeleteView):
    model = Brujka
    template_name = 'order/brujka_confirm_delete.html'
    success_url = reverse_lazy('order:broshka_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'brujka'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.name}" o\'chirildi.')
        return super().form_valid(form)


class BrujkaSearchAPIView(CEORequiredMixin, View):
    """AJAX qidiruv — order formidagi brujka select uchun."""

    def get(self, request):
        q = request.GET.get('q', '').strip()
        qs = Brujka.objects.filter(is_active=True)
        if q:
            qs = qs.filter(name__icontains=q)
        data = [
            {
                'id': b.pk,
                'name': b.name,
                'color': b.color,
                'coating': b.get_coating_type_display(),
                'image': b.image.url if b.image else '',
            }
            for b in qs[:20]
        ]
        return JsonResponse({'results': data})
