from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DeleteView

from apps.order.models import Order, Brujka
from apps.order.forms import OrderForm
from apps.shop.mixins import ShopManagerRequiredMixin

try:
    from apps.casting.models import QuyishJarayon
except ImportError:
    QuyishJarayon = None

try:
    from apps.ilish.models import IlishJarayon, QadoqlashJarayon
except ImportError:
    IlishJarayon = None
    QadoqlashJarayon = None

try:
    from apps.boyash.models import BoyashJarayon
except ImportError:
    BoyashJarayon = None

try:
    from apps.sepish.models import SepishJarayon
except ImportError:
    SepishJarayon = None

try:
    from apps.tosh.models import ToshQadashJarayon
except ImportError:
    ToshQadashJarayon = None


def _order_qs_for_user(user):
    """Foydalanuvchi tomonidan yaratilgan buyurtmalar."""
    return Order.objects.filter(created_by=user).select_related('brujka', 'created_by')


# ── Dashboard ──

class ShopDashboardView(ShopManagerRequiredMixin, View):
    template_name = 'shop/dashboard.html'

    def get(self, request):
        my_orders = _order_qs_for_user(request.user)
        today = timezone.now().date()

        status_counts = {
            'new': my_orders.filter(status=Order.Status.NEW).count(),
            'accepted': my_orders.filter(status=Order.Status.ACCEPTED).count(),
            'in_process': my_orders.filter(status=Order.Status.IN_PROCESS).count(),
            'ready': my_orders.filter(status=Order.Status.READY).count(),
            'delivered': my_orders.filter(status=Order.Status.DELIVERED).count(),
            'cancelled': my_orders.filter(status=Order.Status.CANCELLED).count(),
        }

        overdue = my_orders.filter(
            deadline__lt=today,
        ).exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).count()

        recent_orders = my_orders.order_by('-created_at')[:8]

        urgent_orders = my_orders.filter(
            priority=Order.Priority.URGENT,
        ).exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).order_by('deadline')[:5]

        return render(request, self.template_name, {
            'active_nav': 'dashboard',
            'status_counts': status_counts,
            'total': my_orders.count(),
            'overdue': overdue,
            'recent_orders': recent_orders,
            'urgent_orders': urgent_orders,
            'new_orders_count': status_counts['new'],
        })


# ── Order List ──

class ShopOrderListView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_list.html'

    def get(self, request):
        all_orders = Order.objects.select_related('brujka', 'created_by')
        my_orders = _order_qs_for_user(request.user)
        tab = request.GET.get('tab', 'all')
        q = request.GET.get('q', '').strip()
        priority = request.GET.get('priority', '')
        mine_only = request.GET.get('mine', '') == '1'

        base_qs = my_orders if mine_only else all_orders

        if tab == 'new':
            qs = base_qs.filter(status=Order.Status.NEW)
        elif tab == 'accepted':
            qs = base_qs.filter(status=Order.Status.ACCEPTED)
        elif tab == 'in_process':
            qs = base_qs.filter(status=Order.Status.IN_PROCESS)
        elif tab == 'ready':
            qs = base_qs.filter(status=Order.Status.READY)
        elif tab == 'delivered':
            qs = base_qs.filter(status=Order.Status.DELIVERED)
        elif tab == 'cancelled':
            qs = base_qs.filter(status=Order.Status.CANCELLED)
        else:
            qs = base_qs

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(order_number__icontains=q) | Q(created_by__name__icontains=q))
        if priority:
            qs = qs.filter(priority=priority)

        status_counts = {
            'all': base_qs.count(),
            'new': base_qs.filter(status=Order.Status.NEW).count(),
            'accepted': base_qs.filter(status=Order.Status.ACCEPTED).count(),
            'in_process': base_qs.filter(status=Order.Status.IN_PROCESS).count(),
            'ready': base_qs.filter(status=Order.Status.READY).count(),
            'delivered': base_qs.filter(status=Order.Status.DELIVERED).count(),
            'cancelled': base_qs.filter(status=Order.Status.CANCELLED).count(),
        }

        return render(request, self.template_name, {
            'active_nav': 'orders',
            'orders': qs.order_by('-created_at'),
            'tab': tab,
            'q': q,
            'priority': priority,
            'mine_only': mine_only,
            'status_counts': status_counts,
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })


# ── Order Create ──

class ShopOrderCreateView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': OrderForm(),
            'title': 'Yangi buyurtma',
            'active_nav': 'order_create',
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })

    def post(self, request):
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.status = Order.Status.NEW
            if not order.name.strip() or '#XXXX' in order.name:
                brujka = order.brujka
                bname = brujka.name if brujka else None
                date_str = order.deadline.strftime('%d.%m.%Y') if order.deadline else ''
                order.save()
                if bname and date_str:
                    order.name = f'{order.order_number} {bname} - {date_str}'
                elif bname:
                    order.name = f'{order.order_number} {bname}'
                elif date_str:
                    order.name = f'{order.order_number} - {date_str}'
                else:
                    order.name = order.order_number
                order.save(update_fields=['name'])
            else:
                order.save()
            messages.success(request, f'"{order.name}" buyurtmasi muvaffaqiyatli yaratildi!')
            return redirect('shop:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'title': 'Yangi buyurtma',
            'active_nav': 'order_create',
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })


# ── Order Update ──

class ShopOrderUpdateView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani tahrirlash mumkin emas — allaqachon ishlab chiqarishga ketgan.')
            return redirect('shop:order_detail', pk=pk)
        return render(request, self.template_name, {
            'form': OrderForm(instance=order),
            'order': order,
            'title': f'{order.name} — tahrirlash',
            'active_nav': 'orders',
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani tahrirlash mumkin emas.')
            return redirect('shop:order_detail', pk=pk)
        form = OrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{order.name}" yangilandi.')
            return redirect('shop:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': f'{order.name} — tahrirlash',
            'active_nav': 'orders',
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })


# ── Order Delete ──

class ShopOrderDeleteView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_confirm_delete.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani o\'chirib bo\'lmaydi — ishlab chiqarishda.')
            return redirect('shop:order_detail', pk=pk)
        return render(request, self.template_name, {
            'order': order,
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani o\'chirib bo\'lmaydi.')
            return redirect('shop:order_detail', pk=pk)
        name = order.name
        order.delete()
        messages.success(request, f'"{name}" buyurtmasi o\'chirildi.')
        return redirect('shop:order_list')


# ── Order Cancel ──

class ShopOrderCancelView(ShopManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status in (Order.Status.DELIVERED, Order.Status.CANCELLED):
            messages.error(request, 'Bu buyurtmani bekor qilib bo\'lmaydi.')
        else:
            order.status = Order.Status.CANCELLED
            order.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'"{order.name}" bekor qilindi.')
        return redirect('shop:order_detail', pk=pk)


# ── Order Detail ──

class ShopOrderDetailView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_detail.html'

    def get(self, request, pk):
        from django.db.models import Sum as DSum
        import datetime

        order = get_object_or_404(
            Order.objects.select_related('brujka', 'created_by'),
            pk=pk,
        )

        # Date range filter
        today = timezone.now().date()
        period = request.GET.get('period', 'all')
        date_from_str = request.GET.get('date_from', '')
        date_to_str = request.GET.get('date_to', '')

        if period == 'today':
            date_from = date_to = today
        elif period == 'week':
            date_from = today - datetime.timedelta(days=6)
            date_to = today
        elif period == 'month':
            date_from = today.replace(day=1)
            date_to = today
        elif period == 'custom' and date_from_str and date_to_str:
            try:
                date_from = datetime.date.fromisoformat(date_from_str)
                date_to = datetime.date.fromisoformat(date_to_str)
            except ValueError:
                date_from = date_to = None
        else:
            date_from = date_to = None

        def filter_logs(qs, date_field='sana'):
            if date_from and date_to:
                return qs.filter(**{f'{date_field}__gte': date_from, f'{date_field}__lte': date_to})
            return qs

        departments = []

        # ── Quyish ──
        if QuyishJarayon:
            try:
                from apps.casting.models import QuyishJarayonLog
                casting = order.quyish_jarayon
                logs_qs = filter_logs(casting.loglar.select_related('created_by').order_by('-created_at'))
                total_miqdor = casting.loglar.aggregate(s=DSum('miqdor'))['s'] or 0
                filtered_miqdor = logs_qs.aggregate(s=DSum('miqdor'))['s'] or 0
                logs = [{'sana': l.created_at.date(), 'smena': None, 'son': l.miqdor,
                         'izoh': l.izoh, 'hodim': l.created_by, 'created_at': l.created_at,
                         'extra': l.get_natija_display() if l.natija else ''} for l in logs_qs]
                departments.append({
                    'name': 'Quyish', 'icon': 'casting',
                    'status': casting.get_status_display(), 'status_key': casting.status,
                    'created_at': casting.created_at, 'updated_at': casting.updated_at,
                    'unit': 'dona', 'total': total_miqdor, 'filtered': filtered_miqdor,
                    'logs': logs,
                })
            except Exception:
                pass

        # ── Ilish ──
        if IlishJarayon:
            try:
                ilish = order.ilish_jarayon
                logs_qs = filter_logs(ilish.loglar.select_related('hodim', 'vishilka', 'created_by').order_by('-sana', '-created_at'))
                total_broshka = sum(
                    (l.vishilka.quantity * l.vishilka_soni * 2 if l.vishilka else 0)
                    for l in ilish.loglar.all()
                )
                filtered_broshka = sum(
                    (l.vishilka.quantity * l.vishilka_soni * 2 if l.vishilka else 0)
                    for l in logs_qs
                )
                logs = [{'sana': l.sana, 'smena': l.get_smena_display(), 'son': l.ilingan_broshka,
                         'izoh': l.izoh, 'hodim': l.hodim, 'created_at': l.created_at,
                         'extra': f'{l.vishilka} × {l.vishilka_soni}' if l.vishilka else ''} for l in logs_qs]
                departments.append({
                    'name': 'Ilish', 'icon': 'ilish',
                    'status': ilish.get_status_display(), 'status_key': ilish.status,
                    'created_at': ilish.created_at, 'updated_at': ilish.updated_at,
                    'unit': 'broshka', 'total': total_broshka, 'filtered': filtered_broshka,
                    'logs': logs,
                })
            except Exception:
                pass

        # ── Upakovka ──
        if QadoqlashJarayon:
            try:
                upakovka = order.qadoqlash_jarayon
                logs_qs = filter_logs(upakovka.loglar.select_related('created_by').order_by('-sana', '-created_at'))
                total_par = upakovka.loglar.aggregate(s=DSum('par_soni'))['s'] or 0
                filtered_par = logs_qs.aggregate(s=DSum('par_soni'))['s'] or 0
                logs = [{'sana': l.sana, 'smena': l.get_smena_display(), 'son': l.par_soni,
                         'izoh': l.izoh, 'hodim': l.created_by, 'created_at': l.created_at,
                         'extra': ''} for l in logs_qs]
                departments.append({
                    'name': 'Upakovka', 'icon': 'upakovka',
                    'status': upakovka.get_status_display(), 'status_key': upakovka.status,
                    'created_at': upakovka.created_at, 'updated_at': upakovka.updated_at,
                    'unit': 'par', 'total': total_par, 'filtered': filtered_par,
                    'logs': logs,
                })
            except Exception:
                pass

        # ── Bo'yash ──
        if BoyashJarayon:
            try:
                from apps.boyash.models import BoyashJarayonLog
                boyash = order.boyash_jarayon
                logs_qs = filter_logs(boyash.loglar.select_related('vishilka', 'created_by').order_by('-sana', '-created_at'))
                total_par = sum(
                    (l.vishilka.quantity * l.vishilka_soni if l.vishilka else 0)
                    for l in boyash.loglar.all()
                )
                filtered_par = sum(
                    (l.vishilka.quantity * l.vishilka_soni if l.vishilka else 0)
                    for l in logs_qs
                )
                logs = [{'sana': l.sana, 'smena': l.get_smena_display(), 'son': l.boyalgan_par,
                         'izoh': l.izoh, 'hodim': l.created_by, 'created_at': l.created_at,
                         'extra': f'{l.vishilka} × {l.vishilka_soni}' if l.vishilka else ''} for l in logs_qs]
                departments.append({
                    'name': "Bo'yash", 'icon': 'boyash',
                    'status': boyash.get_status_display(), 'status_key': boyash.status,
                    'created_at': boyash.created_at, 'updated_at': boyash.updated_at,
                    'unit': 'par', 'total': total_par, 'filtered': filtered_par,
                    'logs': logs,
                })
            except Exception:
                pass

        # ── Sepish ──
        if SepishJarayon:
            try:
                sepish = order.sepish_jarayon
                logs_qs = filter_logs(sepish.loglar.select_related('kraska', 'created_by').order_by('-sana', '-created_at'))
                total_par = sepish.loglar.aggregate(s=DSum('par_soni'))['s'] or 0
                filtered_par = logs_qs.aggregate(s=DSum('par_soni'))['s'] or 0
                logs = [{'sana': l.sana, 'smena': l.get_smena_display(), 'son': l.par_soni,
                         'izoh': l.izoh, 'hodim': l.created_by, 'created_at': l.created_at,
                         'extra': f'{l.kraska} {l.kraska_gramm}g' if l.kraska else ''} for l in logs_qs]
                departments.append({
                    'name': 'Sepish', 'icon': 'sepish',
                    'status': sepish.get_status_display(), 'status_key': sepish.status,
                    'created_at': sepish.created_at, 'updated_at': sepish.updated_at,
                    'unit': 'par', 'total': total_par, 'filtered': filtered_par,
                    'logs': logs,
                })
            except Exception:
                pass

        # ── Tosh ──
        if ToshQadashJarayon:
            try:
                tosh = order.tosh_qadash_jarayon
                logs_qs = filter_logs(tosh.loglar.select_related('hodim', 'tosh', 'created_by').order_by('-sana', '-created_at'))
                total_par = tosh.loglar.aggregate(s=DSum('par_soni'))['s'] or 0
                filtered_par = logs_qs.aggregate(s=DSum('par_soni'))['s'] or 0
                logs = [{'sana': l.sana, 'smena': l.get_smena_display(), 'son': l.par_soni,
                         'izoh': l.izoh, 'hodim': l.hodim, 'created_at': l.created_at,
                         'extra': str(l.tosh) if l.tosh else ''} for l in logs_qs]
                departments.append({
                    'name': 'Tosh qadash', 'icon': 'tosh',
                    'status': tosh.get_status_display(), 'status_key': tosh.status,
                    'created_at': tosh.created_at, 'updated_at': tosh.updated_at,
                    'unit': 'par', 'total': total_par, 'filtered': filtered_par,
                    'logs': logs,
                })
            except Exception:
                pass

        is_mine = order.created_by == request.user
        can_edit = is_mine and order.status in (Order.Status.NEW, Order.Status.ACCEPTED)
        can_cancel = is_mine and order.status not in (Order.Status.DELIVERED, Order.Status.CANCELLED)
        can_delete = is_mine and order.status in (Order.Status.NEW, Order.Status.ACCEPTED)

        return render(request, self.template_name, {
            'order': order,
            'departments': departments,
            'can_edit': can_edit,
            'can_cancel': can_cancel,
            'can_delete': can_delete,
            'active_nav': 'orders',
            'period': period,
            'date_from': date_from_str or (date_from.isoformat() if date_from else ''),
            'date_to': date_to_str or (date_to.isoformat() if date_to else ''),
            'today': today.isoformat(),
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })


# ── Broshka List ──

class ShopBroshkaListView(ShopManagerRequiredMixin, View):
    template_name = 'shop/broshka_list.html'

    def get(self, request):
        q = request.GET.get('q', '').strip()
        coating = request.GET.get('coating', '')
        qs = Brujka.objects.filter(is_active=True)
        if q:
            qs = qs.filter(name__icontains=q)
        if coating:
            qs = qs.filter(coating_type=coating)
        return render(request, self.template_name, {
            'broshkalar': qs,
            'q': q,
            'coating': coating,
            'coating_choices': Brujka.CoatingType.choices,
            'active_nav': 'broshkalar',
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })


class ShopBroshkaDetailView(ShopManagerRequiredMixin, View):
    template_name = 'shop/broshka_detail.html'

    def get(self, request, pk):
        broshka = get_object_or_404(Brujka, pk=pk, is_active=True)
        my_orders_with_this = Order.objects.filter(
            created_by=request.user,
            brujka=broshka,
        ).order_by('-created_at')[:10]
        return render(request, self.template_name, {
            'broshka': broshka,
            'my_orders': my_orders_with_this,
            'active_nav': 'broshkalar',
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })


# ── Stats ──

class ShopStatsView(ShopManagerRequiredMixin, View):
    template_name = 'shop/stats.html'

    def get(self, request):
        my_orders = _order_qs_for_user(request.user)
        today = timezone.now().date()

        total = my_orders.count()
        total_qty = my_orders.aggregate(s=Sum('quantity'))['s'] or 0
        delivered = my_orders.filter(status=Order.Status.DELIVERED)
        delivered_count = delivered.count()
        delivered_qty = delivered.aggregate(s=Sum('quantity'))['s'] or 0
        cancelled_count = my_orders.filter(status=Order.Status.CANCELLED).count()
        in_process_count = my_orders.filter(status__in=[
            Order.Status.NEW, Order.Status.ACCEPTED, Order.Status.IN_PROCESS
        ]).count()
        ready_count = my_orders.filter(status=Order.Status.READY).count()
        overdue_count = my_orders.filter(
            deadline__lt=today
        ).exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).count()

        # Oylik statistika (oxirgi 6 oy)
        from collections import defaultdict
        import datetime

        monthly = defaultdict(lambda: {'created': 0, 'delivered': 0, 'qty': 0})
        for o in my_orders.order_by('created_at'):
            key = o.created_at.strftime('%Y-%m')
            monthly[key]['created'] += 1
            monthly[key]['qty'] += o.quantity
            if o.status == Order.Status.DELIVERED:
                monthly[key]['delivered'] += 1

        months = sorted(monthly.keys())[-6:]
        monthly_data = [{'month': m, **monthly[m]} for m in months]

        # Status bo'yicha taqsimot
        status_dist = []
        for st, label in Order.Status.choices:
            cnt = my_orders.filter(status=st).count()
            status_dist.append({'status': st, 'label': label, 'count': cnt})

        # Priority taqsimot
        priority_dist = []
        for pr, label in Order.Priority.choices:
            cnt = my_orders.filter(priority=pr).count()
            priority_dist.append({'priority': pr, 'label': label, 'count': cnt})

        # Broshka bo'yicha top
        top_broshka = []
        from django.db.models import Count as DCount
        broshka_counts = my_orders.exclude(brujka=None).values(
            'brujka__name', 'brujka__color'
        ).annotate(cnt=DCount('id')).order_by('-cnt')[:8]
        for b in broshka_counts:
            top_broshka.append({
                'name': b['brujka__name'],
                'color': b['brujka__color'],
                'count': b['cnt'],
            })

        # Bo'limlar holatini tekshirish (mening buyurtmalarim uchun)
        dept_stats = []
        active_orders = my_orders.exclude(status__in=[Order.Status.CANCELLED])

        casting_total = casting_done = 0
        ilish_total = ilish_done = 0
        upakovka_total = upakovka_done = 0
        boyash_total = boyash_done = 0
        sepish_total = sepish_done = 0
        tosh_total = tosh_done = 0

        for order in active_orders:
            if QuyishJarayon:
                try:
                    j = order.quyish_jarayon
                    casting_total += 1
                    if j.status == 'quyib_bolindi':
                        casting_done += 1
                except Exception:
                    pass
            if IlishJarayon:
                try:
                    j = order.ilish_jarayon
                    ilish_total += 1
                    if j.status == 'ilib_bolindi':
                        ilish_done += 1
                except Exception:
                    pass
            if QadoqlashJarayon:
                try:
                    j = order.qadoqlash_jarayon
                    upakovka_total += 1
                    if j.status == 'qadoqlandi':
                        upakovka_done += 1
                except Exception:
                    pass
            if BoyashJarayon:
                try:
                    j = order.boyash_jarayon
                    boyash_total += 1
                    if j.status == 'boyaldi':
                        boyash_done += 1
                except Exception:
                    pass
            if SepishJarayon:
                try:
                    j = order.sepish_jarayon
                    sepish_total += 1
                    if j.status == 'sepildi':
                        sepish_done += 1
                except Exception:
                    pass
            if ToshQadashJarayon:
                try:
                    j = order.tosh_qadash_jarayon
                    tosh_total += 1
                    if j.status == 'tosh_qadaldi':
                        tosh_done += 1
                except Exception:
                    pass

        dept_stats = [
            {'name': 'Quyish', 'icon': 'casting', 'total': casting_total, 'done': casting_done},
            {'name': 'Ilish', 'icon': 'ilish', 'total': ilish_total, 'done': ilish_done},
            {'name': 'Upakovka', 'icon': 'upakovka', 'total': upakovka_total, 'done': upakovka_done},
            {'name': "Bo'yash", 'icon': 'boyash', 'total': boyash_total, 'done': boyash_done},
            {'name': 'Sepish', 'icon': 'sepish', 'total': sepish_total, 'done': sepish_done},
            {'name': 'Tosh', 'icon': 'tosh', 'total': tosh_total, 'done': tosh_done},
        ]

        return render(request, self.template_name, {
            'active_nav': 'stats',
            'total': total,
            'total_qty': total_qty,
            'delivered_count': delivered_count,
            'delivered_qty': delivered_qty,
            'cancelled_count': cancelled_count,
            'in_process_count': in_process_count,
            'ready_count': ready_count,
            'overdue_count': overdue_count,
            'monthly_data': monthly_data,
            'status_dist': status_dist,
            'priority_dist': priority_dist,
            'top_broshka': top_broshka,
            'dept_stats': dept_stats,
            'new_orders_count': _order_qs_for_user(request.user).filter(status=Order.Status.NEW).count(),
        })
