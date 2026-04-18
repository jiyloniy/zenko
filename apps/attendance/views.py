import base64
import io

import qrcode
from django.core import signing
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.attendance.models import Attendance
from apps.users.models import User

QR_SALT = 'attendance-qr-v2'


def generate_qr_token(user):
    """Hodim va filialni imzolangan token (filialdagi skaner uchun)."""
    if not user.branch_id:
        payload = {'u': user.pk, 'b': None}
    else:
        payload = {'u': user.pk, 'b': user.branch_id}
    return signing.dumps(payload, salt=QR_SALT)


def verify_qr_token(token):
    """
    Tokenni tekshirish. Qaytadi: (user, token_branch_id yoki None).
    Eski tokenlar (faqat int user pk) ham qo'llab-quvvatlanadi.
    """
    try:
        raw = signing.loads(token, salt=QR_SALT, max_age=None)
    except signing.BadSignature:
        try:
            pk = signing.loads(token, salt='attendance-qr', max_age=None)
            if isinstance(pk, int):
                user = User.objects.filter(pk=pk, is_active=True).select_related('branch', 'shift').first()
                return user, None
        except signing.BadSignature:
            pass
        return None, None

    if isinstance(raw, dict):
        uid = raw.get('u')
        bid = raw.get('b')
        user = User.objects.filter(pk=uid, is_active=True).select_related('branch', 'shift').first()
        return user, bid
    return None, None


def _branch_matches(user, kiosk_branch_id, token_branch_id):
    """Filial tekshiruvi: kiosk tanlangan bo'lsa, hodim shu filialda bo'lishi kerak."""
    if not user.branch_id:
        return False, 'Hodimga filial biriktirilmagan'
    if kiosk_branch_id:
        kb = int(kiosk_branch_id)
        if user.branch_id != kb:
            return False, 'Bu QR kod boshqa filial uchun'
        if token_branch_id is not None and token_branch_id != kb:
            return False, 'QR kod bu filial uchun emas'
        return True, ''
    if token_branch_id is not None and token_branch_id != user.branch_id:
        return False, 'QR kod boshqa filial uchun'
    return True, ''


def auto_checkout_expired(user, now):
    """Ochiq (chiqishsiz) eski kun yozuvlarini yopish."""
    today = now.date()
    open_attendances = Attendance.objects.filter(
        user=user,
        check_in__isnull=False,
        check_out__isnull=True,
    )
    for att in open_attendances:
        if att.date < today and att.check_in:
            att.check_out = att.check_in.replace(hour=23, minute=59, second=0, microsecond=0)
            att.save(update_fields=['check_out'])


def _decode_photo_data(photo_raw):
    if not photo_raw or not photo_raw.startswith('data:image'):
        return None
    try:
        _header, b64 = photo_raw.split(',', 1)
        return base64.b64decode(b64)
    except (ValueError, Exception):
        return None


def _save_attendance_photo(attendance, photo_bytes):
    if not photo_bytes:
        return
    fname = f'{attendance.user_id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.jpg'
    attendance.photo.save(fname, ContentFile(photo_bytes), save=True)


def _today_rows(user, today):
    return Attendance.objects.filter(user=user, date=today)


class QRCodeImageView(View):
    """Chiroqli QR (yuvarlak modullar, yuqori tuzatish darajasi)."""

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        token = generate_qr_token(user)

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(token)
        qr.make(fit=True)

        try:
            from qrcode.image.styledpil import StyledPilImage
            from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
            from qrcode.image.styles.colormasks import SolidFillColorMask

            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                color_mask=SolidFillColorMask(
                    back_color=(255, 255, 255),
                    front_color=(15, 23, 42),
                ),
            )
        except Exception:
            img = qr.make_image(fill_color='#0F172A', back_color='#FFFFFF')

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return HttpResponse(buf.getvalue(), content_type='image/png')


class AttendanceKioskView(View):

    def get(self, request):
        branch_id = request.GET.get('branch', '').strip()
        branch_name = ''
        if branch_id.isdigit():
            from apps.users.models import Branch

            b = Branch.objects.filter(pk=int(branch_id)).first()
            if b:
                branch_name = b.name
        return render(
            request,
            'attendance/kiosk.html',
            {
                'kiosk_branch_id': branch_id if branch_id.isdigit() else '',
                'kiosk_branch_name': branch_name,
            },
        )


class CheckInPageView(AttendanceKioskView):
    """Eski URL mosligi."""

    pass


class CheckOutPageView(AttendanceKioskView):
    """Eski URL mosligi."""

    pass


@method_decorator(csrf_exempt, name='dispatch')
class AttendanceScanAPIView(View):
    """
    QR skan: bugun ochiq yozuv bo'lsa — chiqish, aks holda — kirish.
    Filial: POST `branch_id` yoki URL orqali tanlangan filial bilan solishtiriladi.
    """

    def post(self, request):
        token = request.POST.get('token', '').strip()
        kiosk_branch = request.POST.get('branch_id', '').strip()

        if not token:
            return JsonResponse({'ok': False, 'msg': 'Token topilmadi'}, status=400)

        user, token_branch = verify_qr_token(token)
        if not user:
            return JsonResponse({'ok': False, 'msg': 'Noto\'g\'ri QR kod'}, status=400)

        ok_branch, branch_msg = _branch_matches(user, kiosk_branch or None, token_branch)
        if not ok_branch:
            return JsonResponse({'ok': False, 'msg': branch_msg}, status=400)

        now = timezone.localtime()
        today = now.date()
        branch = user.branch

        auto_checkout_expired(user, now)

        photo_raw = request.POST.get('photo', '').strip()
        photo_bytes = _decode_photo_data(photo_raw)

        qs = _today_rows(user, today)

        # 1) Ochiq yozuv — chiqish
        open_att = (
            qs.filter(check_in__isnull=False, check_out__isnull=True)
            .order_by('check_in', 'id')
            .first()
        )
        if open_att:
            if branch:
                open_att.branch = branch
            open_att.check_out = now
            open_att.save(update_fields=['check_out', 'branch'] if branch else ['check_out'])
            return JsonResponse({
                'ok': True,
                'action': 'check_out',
                'msg': f'{user.name} chiqdi',
                'user_name': user.name,
                'time': now.strftime('%H:%M'),
                'worked': open_att.worked_hours_display,
                'status': open_att.status,
                'shift_name': user.shift.name if user.shift_id else '',
                'shift_start': user.shift.start_time.strftime('%H:%M') if user.shift_id else '',
            })

        # 2) Yopilgan kun — ikkinchi marta skan qilish
        if qs.filter(check_in__isnull=False, check_out__isnull=False).exists():
            return JsonResponse({
                'ok': False,
                'msg': 'Bugun davomat allaqachon yopilgan. Vaqtni admin tahrirlashi mumkin.',
            }, status=409)

        # 3) «Kelmadi» yozuvi — QR bilan haqiqiy kirish
        absent_row = qs.filter(
            status=Attendance.STATUS_ABSENT,
            check_in__isnull=True,
        ).order_by('id').first()
        if absent_row:
            absent_row.check_in = now
            absent_row.check_out = None
            if branch:
                absent_row.branch = branch
            absent_row.save()
            _save_attendance_photo(absent_row, photo_bytes)
            is_late = absent_row.status == Attendance.STATUS_LATE
            return JsonResponse({
                'ok': True,
                'action': 'check_in',
                'msg': f'{user.name} kirdi (admin «Kelmadi» yozuvi yangilandi)',
                'user_name': user.name,
                'time': now.strftime('%H:%M'),
                'is_late': is_late,
                'status': absent_row.status,
                'shift_name': user.shift.name if user.shift_id else '',
                'shift_start': user.shift.start_time.strftime('%H:%M') if user.shift_id else '',
            })

        # 4) Yangi kirish
        att = Attendance(
            user=user,
            branch=branch,
            date=today,
            check_in=now,
        )
        att.save()
        _save_attendance_photo(att, photo_bytes)

        is_late = att.status == Attendance.STATUS_LATE
        return JsonResponse({
            'ok': True,
            'action': 'check_in',
            'msg': f'{user.name} kirdi',
            'user_name': user.name,
            'time': now.strftime('%H:%M'),
            'is_late': is_late,
            'status': att.status,
            'shift_name': user.shift.name if user.shift_id else '',
            'shift_start': user.shift.start_time.strftime('%H:%M') if user.shift_id else '',
        })


@method_decorator(csrf_exempt, name='dispatch')
class CheckInAPIView(AttendanceScanAPIView):
    pass


@method_decorator(csrf_exempt, name='dispatch')
class CheckOutAPIView(AttendanceScanAPIView):
    pass
