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
    context_object_name = 'broshkalar'

    def get_queryset(self):
        qs = Brujka.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'broshka'
        ctx['q'] = self.request.GET.get('q', '')
        ctx['total'] = Brujka.objects.count()
        ctx['active_count'] = Brujka.objects.filter(is_active=True).count()
        return ctx


class BrujkaCreateView(CEORequiredMixin, View):
    template_name = 'order/brujka_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': BrujkaForm(),
            'title': 'Yangi broshka',
            'active_nav': 'broshka',
        })

    def post(self, request):
        form = BrujkaForm(request.POST, request.FILES)
        if form.is_valid():
            broshka = form.save()
            messages.success(request, f'"{broshka.name}" broshkasi yaratildi.')
            return redirect('order:broshka_detail', pk=broshka.pk)
        return render(request, self.template_name, {
            'form': form,
            'title': 'Yangi broshka',
            'active_nav': 'broshka',
        })


class BrujkaDetailView(CEORequiredMixin, View):
    template_name = 'order/brujka_detail.html'

    def get(self, request, pk):
        broshka = get_object_or_404(Brujka, pk=pk)
        orders = broshka.orders.select_related('created_by').order_by('-created_at')[:10]
        return render(request, self.template_name, {
            'broshka': broshka,
            'orders': orders,
            'active_nav': 'broshka',
        })


class BrujkaUpdateView(CEORequiredMixin, View):
    template_name = 'order/brujka_form.html'

    def get(self, request, pk):
        broshka = get_object_or_404(Brujka, pk=pk)
        return render(request, self.template_name, {
            'form': BrujkaForm(instance=broshka),
            'broshka': broshka,
            'title': f'{broshka.name} — tahrirlash',
            'active_nav': 'broshka',
        })

    def post(self, request, pk):
        broshka = get_object_or_404(Brujka, pk=pk)
        form = BrujkaForm(request.POST, request.FILES, instance=broshka)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{broshka.name}" yangilandi.')
            return redirect('order:broshka_detail', pk=broshka.pk)
        return render(request, self.template_name, {
            'form': form,
            'broshka': broshka,
            'title': f'{broshka.name} — tahrirlash',
            'active_nav': 'broshka',
        })


class BrujkaDeleteView(CEORequiredMixin, DeleteView):
    model = Brujka
    template_name = 'order/brujka_confirm_delete.html'
    success_url = reverse_lazy('order:broshka_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'broshka'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.name}" o\'chirildi.')
        return super().form_valid(form)


class BrujkaSearchAPIView(View):
    """AJAX qidiruv — order formidagi broshka select uchun. Login bo'lgan har kim."""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'results': []}, status=403)
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
