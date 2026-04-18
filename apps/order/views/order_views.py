from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DeleteView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse

from apps.order.models import (
    Order, CastingStage, MontajStage, HangingStage,
    StoneSettingStage, PackagingStage, WarehouseStage,
    OrderStageLog,
)
from apps.order.forms import OrderForm, OrderStageLogForm
from apps.order.views.mixins import CEORequiredMixin


class OrderListView(CEORequiredMixin, ListView):
    model = Order
    template_name = 'order/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = Order.objects.select_related('created_by')
        status = self.request.GET.get('status')
        stage = self.request.GET.get('stage')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if stage:
            qs = qs.filter(current_stage=stage)
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'orders'
        ctx['statuses'] = Order.Status.choices
        ctx['stages'] = Order.CurrentStage.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['current_stage'] = self.request.GET.get('stage', '')
        ctx['q'] = self.request.GET.get('q', '')
        # stats
        ctx['total'] = Order.objects.count()
        ctx['new_count'] = Order.objects.filter(status=Order.Status.NEW).count()
        ctx['in_process_count'] = Order.objects.filter(status=Order.Status.IN_PROCESS).count()
        ctx['ready_count'] = Order.objects.filter(status=Order.Status.READY).count()
        return ctx


class OrderCreateView(CEORequiredMixin, View):
    template_name = 'order/order_form.html'

    def get(self, request):
        form = OrderForm()
        return render(request, self.template_name, {
            'form': form,
            'title': 'Yangi buyurtma',
            'active_nav': 'orders',
        })

    def post(self, request):
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.save()
            # auto-create all stage records
            CastingStage.objects.create(order=order, total_quantity=order.quantity)
            MontajStage.objects.create(order=order, total_quantity=order.quantity)
            HangingStage.objects.create(order=order, total_quantity=order.quantity)
            StoneSettingStage.objects.create(order=order, total_quantity=order.quantity)
            PackagingStage.objects.create(order=order, total_quantity=order.quantity)
            WarehouseStage.objects.create(order=order)
            messages.success(request, f'"{order.name}" buyurtmasi yaratildi.')
            return redirect('order:order_list')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Yangi buyurtma',
            'active_nav': 'orders',
        })


class OrderUpdateView(CEORequiredMixin, View):
    template_name = 'order/order_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderForm(instance=order)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': f'{order.name} — tahrirlash',
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{order.name}" yangilandi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': f'{order.name} — tahrirlash',
            'active_nav': 'orders',
        })


class OrderDeleteView(CEORequiredMixin, DeleteView):
    model = Order
    template_name = 'order/order_confirm_delete.html'
    success_url = reverse_lazy('order:order_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'orders'
        ctx['cancel_url'] = reverse_lazy('order:order_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.name}" o\'chirildi.')
        return super().form_valid(form)


class OrderStageLogCreateView(CEORequiredMixin, CreateView):
    model = OrderStageLog
    form_class = OrderStageLogForm
    template_name = 'order/stage_log_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(Order, pk=kwargs['order_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.order = self.order
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('order:order_detail', args=[self.order.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.order
        ctx['is_create'] = True
        return ctx


class OrderStageLogUpdateView(CEORequiredMixin, UpdateView):
    model = OrderStageLog
    form_class = OrderStageLogForm
    template_name = 'order/stage_log_form.html'

    def get_success_url(self):
        return reverse('order:order_detail', args=[self.object.order.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.object.order
        ctx['is_create'] = False
        return ctx


class OrderStageLogDeleteView(CEORequiredMixin, DeleteView):
    model = OrderStageLog
    template_name = 'order/stage_log_confirm_delete.html'

    def get_success_url(self):
        return reverse('order:order_detail', args=[self.object.order.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.object.order
        return ctx


class OrderDetailView(CEORequiredMixin, View):
    template_name = 'order/order_detail.html'

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related(
                'created_by', 'casting', 'montaj', 'hanging',
                'stone_setting', 'packaging', 'warehouse',
            ).prefetch_related('outsource_works', 'quality_checks', 'stage_logs'),
            pk=pk,
        )
        stage_filter = request.GET.get('stage', 'all')
        stage_logs = order.stage_logs.select_related('worker', 'accepted_by').order_by('-created_at')
        if stage_filter != 'all':
            stage_logs = stage_logs.filter(stage=stage_filter)
        # Bosqichlar uchun alohida loglar
        casting_logs = order.stage_logs.filter(stage='casting').select_related('worker', 'accepted_by').order_by('-created_at')
        montaj_logs = order.stage_logs.filter(stage='montaj').select_related('worker', 'accepted_by').order_by('-created_at')
        hanging_logs = order.stage_logs.filter(stage='hanging').select_related('worker', 'accepted_by').order_by('-created_at')
        stone_logs = order.stage_logs.filter(stage='stone_setting').select_related('worker', 'accepted_by').order_by('-created_at')
        packaging_logs = order.stage_logs.filter(stage='packaging').select_related('worker', 'accepted_by').order_by('-created_at')
        warehouse_logs = order.stage_logs.filter(stage='warehouse').select_related('worker', 'accepted_by').order_by('-created_at')
        return render(request, self.template_name, {
            'order': order,
            'stage_logs': stage_logs,
            'active_nav': 'orders',
            'stage_filter': stage_filter,
            'casting_logs': casting_logs,
            'montaj_logs': montaj_logs,
            'hanging_logs': hanging_logs,
            'stone_logs': stone_logs,
            'packaging_logs': packaging_logs,
            'warehouse_logs': warehouse_logs,
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        set_status = request.POST.get('set_status')
        if set_status and set_status in dict(Order.Status.choices):
            order.status = set_status
            order.save(update_fields=['status'])
            messages.success(request, 'Buyurtma holati yangilandi!')
        return redirect(request.path)
