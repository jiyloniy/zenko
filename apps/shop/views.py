import datetime
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import Order, Brujka
from apps.shop.forms import ShopOrderForm
from apps.shop.mixins import ShopManagerRequiredMixin

# ── Lazy imports — bo'limlar mavjud bo'lmasa None ──
try:
    from apps.casting.models import QuyishJarayon, QuyishJarayonLog, HomMahsulotLog
except ImportError:
    QuyishJarayon = QuyishJarayonLog = HomMahsulotLog = None

try:
    from apps.ilish.models import (
        IlishJarayon, IlishJarayonLog,
        QadoqlashJarayon, QadoqlashLog,
    )
except ImportError:
    IlishJarayon = IlishJarayonLog = None
    QadoqlashJarayon = QadoqlashLog = None

try:
    from apps.boyash.models import BoyashJarayon, BoyashJarayonLog
except ImportError:
    BoyashJarayon = BoyashJarayonLog = None

try:
    from apps.sepish.models import SepishJarayon, SepishJarayonLog
except ImportError:
    SepishJarayon = SepishJarayonLog = None

try:
    from apps.tosh.models import ToshQadashJarayon, ToshQadashLog
except ImportError:
    ToshQadashJarayon = ToshQadashLog = None


# ── Helpers ──

def _my_orders(user):
    return Order.objects.filter(created_by=user).select_related('brujka', 'created_by')


def _all_orders():
    return Order.objects.select_related('brujka', 'created_by')


def _new_count(user):
    return _my_orders(user).filter(status=Order.Status.NEW).count()


def _parse_period(request):
    """GET params dan date_from, date_to qaytaradi."""
    today = timezone.now().date()
    period = request.GET.get('period', 'all')
    date_from_str = request.GET.get('date_from', '')
    date_to_str   = request.GET.get('date_to', '')

    if period == 'today':
        date_from = date_to = today
    elif period == 'week':
        date_from = today - datetime.timedelta(days=6)
        date_to   = today
    elif period == 'month':
        date_from = today.replace(day=1)
        date_to   = today
    elif period == 'custom' and date_from_str and date_to_str:
        try:
            date_from = datetime.date.fromisoformat(date_from_str)
            date_to   = datetime.date.fromisoformat(date_to_str)
        except ValueError:
            date_from = date_to = None
    else:
        date_from = date_to = None

    return period, date_from, date_to, date_from_str, date_to_str


def _filter_by_date(qs, date_from, date_to, field='sana'):
    if not (date_from and date_to):
        return qs
    if field == 'created_at':
        return qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    return qs.filter(**{f'{field}__gte': date_from, f'{field}__lte': date_to})


# ── Dashboard ──

class ShopDashboardView(ShopManagerRequiredMixin, View):
    template_name = 'shop/dashboard.html'

    def get(self, request):
        all_q = _all_orders()
        today = timezone.now().date()

        status_counts = {s: all_q.filter(status=s).count() for s, _ in Order.Status.choices}

        overdue = all_q.filter(deadline__lt=today).exclude(
            status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]
        ).count()

        return render(request, self.template_name, {
            'active_nav': 'dashboard',
            'status_counts': status_counts,
            'total': all_q.count(),
            'overdue': overdue,
            'recent_orders': all_q.order_by('-created_at')[:8],
            'urgent_orders': all_q.filter(priority=Order.Priority.URGENT).exclude(
                status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]
            ).order_by('deadline')[:5],
            'new_orders_count': _new_count(request.user),
        })


# ── Order List ──

class ShopOrderListView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_list.html'

    def get(self, request):
        all_q  = _all_orders()
        my_q   = _my_orders(request.user)
        tab      = request.GET.get('tab', 'all')
        q        = request.GET.get('q', '').strip()
        priority = request.GET.get('priority', '')
        mine_only = request.GET.get('mine', '') == '1'

        base = my_q if mine_only else all_q

        STATUS_MAP = {
            'new': Order.Status.NEW, 'accepted': Order.Status.ACCEPTED,
            'in_process': Order.Status.IN_PROCESS, 'ready': Order.Status.READY,
            'delivered': Order.Status.DELIVERED, 'cancelled': Order.Status.CANCELLED,
        }
        qs = base.filter(status=STATUS_MAP[tab]) if tab in STATUS_MAP else base

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(order_number__icontains=q) | Q(created_by__name__icontains=q))
        if priority:
            qs = qs.filter(priority=priority)

        counts = {'all': base.count()}
        counts.update({s: base.filter(status=s).count() for s, _ in Order.Status.choices})

        return render(request, self.template_name, {
            'active_nav': 'orders',
            'orders': qs.order_by('-created_at'),
            'tab': tab, 'q': q, 'priority': priority, 'mine_only': mine_only,
            'status_counts': counts,
            'new_orders_count': _new_count(request.user),
        })


# ── Order Create ──

class ShopOrderCreateView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': ShopOrderForm(), 'title': 'Yangi buyurtma',
            'active_nav': 'order_create', 'new_orders_count': _new_count(request.user),
        })

    def post(self, request):
        form = ShopOrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.status = Order.Status.NEW          # Har doim NEW
            if not order.name.strip() or '#XXXX' in order.name:
                brujka    = order.brujka
                bname     = brujka.name if brujka else None
                date_str  = order.deadline.strftime('%d.%m.%Y') if order.deadline else ''
                order.save()
                parts = [p for p in [order.order_number, bname, f'- {date_str}' if date_str else None] if p]
                order.name = ' '.join(parts)
                order.save(update_fields=['name'])
            else:
                order.save()
            messages.success(request, f'"{order.name}" buyurtmasi yaratildi!')
            return redirect('shop:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form, 'title': 'Yangi buyurtma',
            'active_nav': 'order_create', 'new_orders_count': _new_count(request.user),
        })


# ── Order Update ──

class ShopOrderUpdateView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani tahrirlash mumkin emas.')
            return redirect('shop:order_detail', pk=pk)
        return render(request, self.template_name, {
            'form': ShopOrderForm(instance=order), 'order': order,
            'title': f'{order.name} — tahrirlash', 'active_nav': 'orders',
            'new_orders_count': _new_count(request.user),
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani tahrirlash mumkin emas.')
            return redirect('shop:order_detail', pk=pk)
        form = ShopOrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{order.name}" yangilandi.')
            return redirect('shop:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form, 'order': order,
            'title': f'{order.name} — tahrirlash', 'active_nav': 'orders',
            'new_orders_count': _new_count(request.user),
        })


# ── Order Delete ──

class ShopOrderDeleteView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_confirm_delete.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani o\'chirib bo\'lmaydi.')
            return redirect('shop:order_detail', pk=pk)
        return render(request, self.template_name, {'order': order, 'active_nav': 'orders'})

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        if order.status not in (Order.Status.NEW, Order.Status.ACCEPTED):
            messages.error(request, 'Bu buyurtmani o\'chirib bo\'lmaydi.')
            return redirect('shop:order_detail', pk=pk)
        name = order.name
        order.delete()
        messages.success(request, f'"{name}" o\'chirildi.')
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

def _build_departments(order, date_from, date_to):
    """Har bir bo'lim uchun jarayon + loglar dict qaytaradi."""
    depts = []

    # ── Quyish — HomMahsulotLog (order.hom_loglar) ──
    if HomMahsulotLog:
        try:
            casting   = order.quyish_jarayon           # related_name='quyish_jarayon'
            all_logs  = order.hom_loglar.select_related('stanok', 'created_by')
            filt_logs = _filter_by_date(all_logs, date_from, date_to, field='sana')
            total     = all_logs.aggregate(s=Sum('miqdor'))['s'] or 0
            filtered  = filt_logs.aggregate(s=Sum('miqdor'))['s'] or 0
            logs = [{
                'sana': l.sana,
                'smena': l.get_smena_display() if hasattr(l, 'get_smena_display') else l.smena,
                'son': l.miqdor, 'hodim': l.created_by,
                'extra': str(l.stanok) if l.stanok else '',
                'izoh': l.izoh,
            } for l in filt_logs.order_by('-sana', '-created_at')]
            depts.append({
                'name': 'Quyish', 'icon': 'casting', 'unit': 'par',
                'status': casting.get_status_display(), 'status_key': casting.status,
                'created_at': casting.created_at, 'updated_at': casting.updated_at,
                'total': total, 'filtered': filtered, 'logs': logs,
            })
        except Exception:
            pass

    # ── Ilish ──
    if IlishJarayonLog:
        try:
            ilish     = order.ilish_jarayon            # related_name='ilish_jarayon'
            all_logs  = ilish.loglar.select_related('hodim', 'vishilka', 'created_by')
            filt_logs = _filter_by_date(all_logs, date_from, date_to)
            # broshka = par * 2
            def _broshka(qs):
                return sum(
                    l.vishilka.quantity * l.vishilka_soni * 2 if l.vishilka else 0
                    for l in qs
                )
            total    = _broshka(all_logs)
            filtered = _broshka(filt_logs)
            logs = [{
                'sana': l.sana, 'smena': l.get_smena_display(),
                'son': (l.vishilka.quantity * l.vishilka_soni * 2 if l.vishilka else 0),
                'hodim': l.hodim,
                'extra': f'{l.vishilka} × {l.vishilka_soni}' if l.vishilka else '',
                'izoh': l.izoh,
            } for l in filt_logs.order_by('-sana', '-created_at')]
            depts.append({
                'name': 'Ilish', 'icon': 'ilish', 'unit': 'broshka',
                'status': ilish.get_status_display(), 'status_key': ilish.status,
                'created_at': ilish.created_at, 'updated_at': ilish.updated_at,
                'total': total, 'filtered': filtered, 'logs': logs,
            })
        except Exception:
            pass

    # ── Upakovka ──
    if QadoqlashLog:
        try:
            upakovka  = order.qadoqlash_jarayon        # related_name='qadoqlash_jarayon'
            all_logs  = upakovka.loglar.select_related('created_by')
            filt_logs = _filter_by_date(all_logs, date_from, date_to)
            total     = all_logs.aggregate(s=Sum('par_soni'))['s'] or 0
            filtered  = filt_logs.aggregate(s=Sum('par_soni'))['s'] or 0
            logs = [{
                'sana': l.sana, 'smena': l.get_smena_display(),
                'son': l.par_soni, 'hodim': l.created_by,
                'extra': '', 'izoh': l.izoh,
            } for l in filt_logs.order_by('-sana', '-created_at')]
            depts.append({
                'name': 'Upakovka', 'icon': 'upakovka', 'unit': 'par',
                'status': upakovka.get_status_display(), 'status_key': upakovka.status,
                'created_at': upakovka.created_at, 'updated_at': upakovka.updated_at,
                'total': total, 'filtered': filtered, 'logs': logs,
            })
        except Exception:
            pass

    # ── Bo'yash ──
    if BoyashJarayonLog:
        try:
            boyash    = order.boyash_jarayon           # related_name='boyash_jarayon'
            all_logs  = boyash.loglar.select_related('vishilka', 'created_by')
            filt_logs = _filter_by_date(all_logs, date_from, date_to)
            def _par(qs):
                return sum(
                    l.vishilka.quantity * l.vishilka_soni if l.vishilka else 0
                    for l in qs
                )
            total    = _par(all_logs)
            filtered = _par(filt_logs)
            logs = [{
                'sana': l.sana, 'smena': l.get_smena_display(),
                'son': (l.vishilka.quantity * l.vishilka_soni if l.vishilka else 0),
                'hodim': l.created_by,
                'extra': f'{l.vishilka} × {l.vishilka_soni}' if l.vishilka else '',
                'izoh': l.izoh,
            } for l in filt_logs.order_by('-sana', '-created_at')]
            depts.append({
                'name': "Bo'yash", 'icon': 'boyash', 'unit': 'par',
                'status': boyash.get_status_display(), 'status_key': boyash.status,
                'created_at': boyash.created_at, 'updated_at': boyash.updated_at,
                'total': total, 'filtered': filtered, 'logs': logs,
            })
        except Exception:
            pass

    # ── Sepish ──
    if SepishJarayonLog:
        try:
            sepish    = order.sepish_jarayon           # related_name='sepish_jarayon'
            all_logs  = sepish.loglar.select_related('kraska', 'created_by')
            filt_logs = _filter_by_date(all_logs, date_from, date_to)
            total     = all_logs.aggregate(s=Sum('par_soni'))['s'] or 0
            filtered  = filt_logs.aggregate(s=Sum('par_soni'))['s'] or 0
            logs = [{
                'sana': l.sana, 'smena': l.get_smena_display(),
                'son': l.par_soni, 'hodim': l.created_by,
                'extra': f'{l.kraska} — {l.kraska_gramm}g' if l.kraska else '',
                'izoh': l.izoh,
            } for l in filt_logs.order_by('-sana', '-created_at')]
            depts.append({
                'name': 'Sepish', 'icon': 'sepish', 'unit': 'par',
                'status': sepish.get_status_display(), 'status_key': sepish.status,
                'created_at': sepish.created_at, 'updated_at': sepish.updated_at,
                'total': total, 'filtered': filtered, 'logs': logs,
            })
        except Exception:
            pass

    # ── Tosh ──
    if ToshQadashLog:
        try:
            tosh      = order.tosh_jarayon             # related_name='tosh_jarayon'
            all_logs  = tosh.loglar.select_related('hodim', 'tosh', 'created_by')
            filt_logs = _filter_by_date(all_logs, date_from, date_to)
            total     = all_logs.aggregate(s=Sum('par_soni'))['s'] or 0
            filtered  = filt_logs.aggregate(s=Sum('par_soni'))['s'] or 0
            logs = [{
                'sana': l.sana, 'smena': l.get_smena_display(),
                'son': l.par_soni, 'hodim': l.hodim,
                'extra': str(l.tosh) if l.tosh else '',
                'izoh': l.izoh,
            } for l in filt_logs.order_by('-sana', '-created_at')]
            depts.append({
                'name': 'Tosh qadash', 'icon': 'tosh', 'unit': 'par',
                'status': tosh.get_status_display(), 'status_key': tosh.status,
                'created_at': tosh.created_at, 'updated_at': tosh.updated_at,
                'total': total, 'filtered': filtered, 'logs': logs,
            })
        except Exception:
            pass

    return depts


class ShopOrderDetailView(ShopManagerRequiredMixin, View):
    template_name = 'shop/order_detail.html'

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related('brujka', 'created_by'), pk=pk
        )
        period, date_from, date_to, df_str, dt_str = _parse_period(request)
        departments = _build_departments(order, date_from, date_to)

        is_mine    = order.created_by == request.user
        can_edit   = is_mine and order.status in (Order.Status.NEW, Order.Status.ACCEPTED)
        can_cancel = is_mine and order.status not in (Order.Status.DELIVERED, Order.Status.CANCELLED)
        can_delete = is_mine and order.status in (Order.Status.NEW, Order.Status.ACCEPTED)
        today      = timezone.now().date()

        return render(request, self.template_name, {
            'order': order, 'departments': departments,
            'can_edit': can_edit, 'can_cancel': can_cancel, 'can_delete': can_delete,
            'active_nav': 'orders', 'period': period,
            'date_from': df_str or (date_from.isoformat() if date_from else ''),
            'date_to':   dt_str or (date_to.isoformat()   if date_to   else ''),
            'today': today.isoformat(),
            'new_orders_count': _new_count(request.user),
        })


# ── Logs ──

def _build_global_logs(date_from, date_to):
    """Barcha bo'limlar uchun global log ro'yxati."""
    depts = []

    if QuyishJarayonLog:
        try:
            qs = _filter_by_date(
                QuyishJarayonLog.objects.select_related(
                    'jarayon__order__brujka', 'created_by'
                ).order_by('-created_at'),
                date_from, date_to, field='created_at'
            )
            total = qs.aggregate(s=Sum('miqdor'))['s'] or 0
            depts.append({
                'name': 'Quyish', 'icon': 'casting', 'unit': 'dona',
                'total': total, 'count': qs.count(),
                'logs': [{
                    'sana': l.created_at.date(), 'smena': None,
                    'son': l.miqdor, 'hodim': l.created_by,
                    'order': l.jarayon.order if l.jarayon_id else None,
                    'extra': l.get_natija_display() if l.natija else '',
                    'izoh': l.izoh,
                } for l in qs[:200]],
            })
        except Exception:
            pass

    if IlishJarayonLog:
        try:
            qs = _filter_by_date(
                IlishJarayonLog.objects.select_related(
                    'jarayon__order__brujka', 'hodim', 'vishilka', 'created_by'
                ).order_by('-sana', '-created_at'),
                date_from, date_to
            )
            total = sum(
                l.vishilka.quantity * l.vishilka_soni * 2 if l.vishilka else 0
                for l in qs
            )
            depts.append({
                'name': 'Ilish', 'icon': 'ilish', 'unit': 'broshka',
                'total': total, 'count': qs.count(),
                'logs': [{
                    'sana': l.sana, 'smena': l.get_smena_display(),
                    'son': (l.vishilka.quantity * l.vishilka_soni * 2 if l.vishilka else 0),
                    'hodim': l.hodim,
                    'order': l.jarayon.order if l.jarayon_id else None,
                    'extra': f'{l.vishilka} × {l.vishilka_soni}' if l.vishilka else '',
                    'izoh': l.izoh,
                } for l in qs[:200]],
            })
        except Exception:
            pass

    if QadoqlashLog:
        try:
            qs = _filter_by_date(
                QadoqlashLog.objects.select_related(
                    'jarayon__order__brujka', 'created_by'
                ).order_by('-sana', '-created_at'),
                date_from, date_to
            )
            total = qs.aggregate(s=Sum('par_soni'))['s'] or 0
            depts.append({
                'name': 'Upakovka', 'icon': 'upakovka', 'unit': 'par',
                'total': total, 'count': qs.count(),
                'logs': [{
                    'sana': l.sana, 'smena': l.get_smena_display(),
                    'son': l.par_soni, 'hodim': l.created_by,
                    'order': l.jarayon.order if l.jarayon_id else None,
                    'extra': '', 'izoh': l.izoh,
                } for l in qs[:200]],
            })
        except Exception:
            pass

    if BoyashJarayonLog:
        try:
            qs = _filter_by_date(
                BoyashJarayonLog.objects.select_related(
                    'jarayon__order__brujka', 'vishilka', 'created_by'
                ).order_by('-sana', '-created_at'),
                date_from, date_to
            )
            total = sum(
                l.vishilka.quantity * l.vishilka_soni if l.vishilka else 0
                for l in qs
            )
            depts.append({
                'name': "Bo'yash", 'icon': 'boyash', 'unit': 'par',
                'total': total, 'count': qs.count(),
                'logs': [{
                    'sana': l.sana, 'smena': l.get_smena_display(),
                    'son': (l.vishilka.quantity * l.vishilka_soni if l.vishilka else 0),
                    'hodim': l.created_by,
                    'order': l.jarayon.order if l.jarayon_id else None,
                    'extra': f'{l.vishilka} × {l.vishilka_soni}' if l.vishilka else '',
                    'izoh': l.izoh,
                } for l in qs[:200]],
            })
        except Exception:
            pass

    if SepishJarayonLog:
        try:
            qs = _filter_by_date(
                SepishJarayonLog.objects.select_related(
                    'jarayon__order__brujka', 'kraska', 'created_by'
                ).order_by('-sana', '-created_at'),
                date_from, date_to
            )
            total = qs.aggregate(s=Sum('par_soni'))['s'] or 0
            depts.append({
                'name': 'Sepish', 'icon': 'sepish', 'unit': 'par',
                'total': total, 'count': qs.count(),
                'logs': [{
                    'sana': l.sana, 'smena': l.get_smena_display(),
                    'son': l.par_soni, 'hodim': l.created_by,
                    'order': l.jarayon.order if l.jarayon_id else None,
                    'extra': f'{l.kraska} — {l.kraska_gramm}g' if l.kraska else '',
                    'izoh': l.izoh,
                } for l in qs[:200]],
            })
        except Exception:
            pass

    if ToshQadashLog:
        try:
            qs = _filter_by_date(
                ToshQadashLog.objects.select_related(
                    'jarayon__order__brujka', 'hodim', 'tosh', 'created_by'
                ).order_by('-sana', '-created_at'),
                date_from, date_to
            )
            total = qs.aggregate(s=Sum('par_soni'))['s'] or 0
            depts.append({
                'name': 'Tosh qadash', 'icon': 'tosh', 'unit': 'par',
                'total': total, 'count': qs.count(),
                'logs': [{
                    'sana': l.sana, 'smena': l.get_smena_display(),
                    'son': l.par_soni, 'hodim': l.hodim,
                    'order': l.jarayon.order if l.jarayon_id else None,
                    'extra': str(l.tosh) if l.tosh else '',
                    'izoh': l.izoh,
                } for l in qs[:200]],
            })
        except Exception:
            pass

    return depts


class ShopLogsView(ShopManagerRequiredMixin, View):
    template_name = 'shop/logs.html'

    def get(self, request):
        today  = timezone.now().date()
        period = request.GET.get('period', 'today')
        date_from_str = request.GET.get('date_from', '')
        date_to_str   = request.GET.get('date_to', '')

        if period == 'today':
            date_from = date_to = today
        elif period == 'week':
            date_from = today - datetime.timedelta(days=6)
            date_to   = today
        elif period == 'month':
            date_from = today.replace(day=1)
            date_to   = today
        elif period == 'custom' and date_from_str and date_to_str:
            try:
                date_from = datetime.date.fromisoformat(date_from_str)
                date_to   = datetime.date.fromisoformat(date_to_str)
            except ValueError:
                date_from = date_to = today
        else:
            date_from = date_to = today

        departments = _build_global_logs(date_from, date_to)

        return render(request, self.template_name, {
            'active_nav': 'logs', 'departments': departments,
            'period': period,
            'date_from': date_from_str or date_from.isoformat(),
            'date_to':   date_to_str   or date_to.isoformat(),
            'date_from_obj': date_from, 'date_to_obj': date_to,
            'today': today.isoformat(),
            'new_orders_count': _new_count(request.user),
        })


# ── Stats ──

class ShopStatsView(ShopManagerRequiredMixin, View):
    template_name = 'shop/stats.html'

    def get(self, request):
        all_q = _all_orders()
        today = timezone.now().date()

        total        = all_q.count()
        total_qty    = all_q.aggregate(s=Sum('quantity'))['s'] or 0
        delivered    = all_q.filter(status=Order.Status.DELIVERED)
        del_count    = delivered.count()
        del_qty      = delivered.aggregate(s=Sum('quantity'))['s'] or 0
        cancelled    = all_q.filter(status=Order.Status.CANCELLED).count()
        in_proc      = all_q.filter(status__in=[Order.Status.NEW, Order.Status.ACCEPTED, Order.Status.IN_PROCESS]).count()
        ready        = all_q.filter(status=Order.Status.READY).count()
        overdue      = all_q.filter(deadline__lt=today).exclude(
            status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).count()

        # Oylik (oxirgi 6 oy)
        from collections import defaultdict
        monthly = defaultdict(lambda: {'created': 0, 'delivered': 0, 'qty': 0})
        for o in all_q.order_by('created_at'):
            key = o.created_at.strftime('%Y-%m')
            monthly[key]['created'] += 1
            monthly[key]['qty']     += o.quantity
            if o.status == Order.Status.DELIVERED:
                monthly[key]['delivered'] += 1
        months       = sorted(monthly)[-6:]
        monthly_data = [{'month': m, **monthly[m]} for m in months]

        # Status taqsimot
        status_dist = [
            {'status': s, 'label': l, 'count': all_q.filter(status=s).count()}
            for s, l in Order.Status.choices
        ]
        # Priority taqsimot
        priority_dist = [
            {'priority': p, 'label': l, 'count': all_q.filter(priority=p).count()}
            for p, l in Order.Priority.choices
        ]
        # Top broshka
        top_broshka = list(
            all_q.exclude(brujka=None)
            .values('brujka__name', 'brujka__color')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')[:8]
        )

        # Bo'limlar progressi (barcha aktiv orderlar bo'yicha)
        active_orders = list(all_q.exclude(status__in=[Order.Status.CANCELLED]).prefetch_related(
            'quyish_jarayon', 'ilish_jarayon', 'qadoqlash_jarayon',
            'boyash_jarayon', 'sepish_jarayon', 'tosh_jarayon',
        ))

        def _dept_stat(related, done_statuses):
            total_d = done_d = 0
            for o in active_orders:
                try:
                    j = getattr(o, related)
                    total_d += 1
                    if j.status in done_statuses:
                        done_d += 1
                except Exception:
                    pass
            return total_d, done_d

        dept_stats = []
        if QuyishJarayon:
            t, d = _dept_stat('quyish_jarayon', ['quyib_bolindi'])
            dept_stats.append({'name': 'Quyish', 'icon': 'casting', 'total': t, 'done': d})
        if IlishJarayon:
            t, d = _dept_stat('ilish_jarayon', ['ilib_bolindi'])
            dept_stats.append({'name': 'Ilish', 'icon': 'ilish', 'total': t, 'done': d})
        if QadoqlashJarayon:
            t, d = _dept_stat('qadoqlash_jarayon', ['qadoqlandi'])
            dept_stats.append({'name': 'Upakovka', 'icon': 'upakovka', 'total': t, 'done': d})
        if BoyashJarayon:
            t, d = _dept_stat('boyash_jarayon', ['boyaldi'])
            dept_stats.append({'name': "Bo'yash", 'icon': 'boyash', 'total': t, 'done': d})
        if SepishJarayon:
            t, d = _dept_stat('sepish_jarayon', ['sepildi'])
            dept_stats.append({'name': 'Sepish', 'icon': 'sepish', 'total': t, 'done': d})
        if ToshQadashJarayon:
            t, d = _dept_stat('tosh_jarayon', ['tosh_qadaldi'])
            dept_stats.append({'name': 'Tosh qadash', 'icon': 'tosh', 'total': t, 'done': d})

        return render(request, self.template_name, {
            'active_nav': 'stats',
            'total': total, 'total_qty': total_qty,
            'delivered_count': del_count, 'delivered_qty': del_qty,
            'cancelled_count': cancelled, 'in_process_count': in_proc,
            'ready_count': ready, 'overdue_count': overdue,
            'monthly_data': monthly_data,
            'status_dist': status_dist, 'priority_dist': priority_dist,
            'top_broshka': top_broshka, 'dept_stats': dept_stats,
            'new_orders_count': _new_count(request.user),
        })


# ── Broshka List ──

class ShopBroshkaListView(ShopManagerRequiredMixin, View):
    template_name = 'shop/broshka_list.html'

    def get(self, request):
        q      = request.GET.get('q', '').strip()
        coating = request.GET.get('coating', '')
        qs = Brujka.objects.filter(is_active=True)
        if q:
            qs = qs.filter(name__icontains=q)
        if coating:
            qs = qs.filter(coating_type=coating)
        return render(request, self.template_name, {
            'broshkalar': qs, 'q': q, 'coating': coating,
            'coating_choices': Brujka.CoatingType.choices,
            'active_nav': 'broshkalar',
            'new_orders_count': _new_count(request.user),
        })


class ShopBroshkaDetailView(ShopManagerRequiredMixin, View):
    template_name = 'shop/broshka_detail.html'

    def get(self, request, pk):
        broshka = get_object_or_404(Brujka, pk=pk, is_active=True)
        return render(request, self.template_name, {
            'broshka': broshka,
            'my_orders': Order.objects.filter(
                created_by=request.user, brujka=broshka
            ).order_by('-created_at')[:10],
            'active_nav': 'broshkalar',
            'new_orders_count': _new_count(request.user),
        })
