import io
import base64
from datetime import date

import qrcode
from django.contrib import messages
from django.core import signing
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.attendance.models import Attendance
from apps.users.models import Shift, User


# ── QR Code Generation ──

QR_SALT = 'attendance-qr'


def generate_qr_token(user):
    """Sign user pk for QR code."""
    return signing.dumps(user.pk, salt=QR_SALT)


def verify_qr_token(token):
    """Verify QR token and return user, or None."""
    try:
        pk = signing.loads(token, salt=QR_SALT, max_age=None)
        return User.objects.select_related('branch', 'shift').get(pk=pk, is_active=True)
    except (signing.BadSignature, User.DoesNotExist):
        return None


def auto_checkout_expired(user, now):
    """Smena vaqti o'tgan, lekin check_out qilinmagan davomatlarni avtomatik yopish.
    Oldingi kunlardagi ochiq davomatlarni ham yopadi.
    """
    today = now.date()
    open_attendances = Attendance.objects.filter(
        user=user,
        check_in__isnull=False,
        check_out__isnull=True,
    ).select_related('shift')

    for att in open_attendances:
        if att.date < today:
            # Oldingi kunlarni avtomatik yopish
            if att.shift and att.shift.end_time:
                close_time = att.check_in.replace(
                    hour=att.shift.end_time.hour,
                    minute=att.shift.end_time.minute,
                    second=0, microsecond=0,
                )
                att.check_out = close_time
            else:
                # Smenasiz — kirish kuni oxirida yopish
                att.check_out = att.check_in.replace(hour=23, minute=59, second=0, microsecond=0)
            att.save(update_fields=['check_out'])
        elif att.shift and att.shift.end_time:
            # Bugungi kun — smena vaqti o'tganmi?
            shift_end = now.replace(
                hour=att.shift.end_time.hour,
                minute=att.shift.end_time.minute,
                second=0, microsecond=0,
            )
            if now >= shift_end:
                att.check_out = shift_end
                att.save(update_fields=['check_out'])


class QRCodeImageView(View):
    """Generate QR code PNG for a user."""

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        token = generate_qr_token(user)

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(token)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#1A1A1A', back_color='white')

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return HttpResponse(buf.getvalue(), content_type='image/png')


# ── Kiosk Page (Combined) ──

class AttendanceKioskView(View):
    """Bitta sahifa — kirish va chiqish uchun."""

    def get(self, request):
        return render(request, 'attendance/kiosk.html')


# ── Legacy views for backward compatibility ──

class CheckInPageView(View):
    def get(self, request):
        return render(request, 'attendance/kiosk.html')


class CheckOutPageView(View):
    def get(self, request):
        return render(request, 'attendance/kiosk.html')


# ── Smart API endpoint ──

@method_decorator(csrf_exempt, name='dispatch')
class AttendanceScanAPIView(View):
    """
    Yagona API endpoint — QR skanerlanganda:
    1. Agar bugun kirish qilinmagan bo'lsa → KIRISH
    2. Agar kirish qilingan, chiqish yo'q → CHIQISH
    3. Agar asosiy smena tugagan, yana skanerlasa → QO'SHIMCHA SMENA kirish
    """

    def post(self, request):
        token = request.POST.get('token', '').strip()
        if not token:
            return JsonResponse({'ok': False, 'msg': 'Token topilmadi'}, status=400)

        user = verify_qr_token(token)
        if not user:
            return JsonResponse({'ok': False, 'msg': 'Noto\'g\'ri yoki muddati o\'tgan QR kod'}, status=400)

        if not user.branch:
            return JsonResponse({'ok': False, 'msg': 'Hodimga filial biriktirilmagan'}, status=400)

        # Rasmni olish (base64 yoki file)
        photo_file = None
        photo_b64 = request.POST.get('photo', '').strip()
        if photo_b64:
            try:
                if ',' in photo_b64:
                    photo_b64 = photo_b64.split(',', 1)[1]
                photo_data = base64.b64decode(photo_b64)
                photo_file = ContentFile(photo_data, name=f'{user.pk}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.jpg')
            except Exception:
                photo_file = None

        now = timezone.localtime()
        today = now.date()

        # Avval smena vaqti o'tganlarni avtomatik yopish
        auto_checkout_expired(user, now)

        # Bugun ochiq davomat bormi? (check_in bor, check_out yo'q)
        open_att = Attendance.objects.filter(
            user=user,
            date=today,
            check_in__isnull=False,
            check_out__isnull=True,
        ).select_related('shift').first()

        if open_att:
            # CHIQISH
            return self._do_checkout(user, open_att, now, photo_file)
        else:
            # KIRISH yoki QO'SHIMCHA SMENA
            return self._do_checkin(user, now, today, photo_file)

    def _do_checkin(self, user, now, today, photo_file=None):
        """Kirish yoki qo'shimcha smena kirish."""
        target_shift = user.shift
        is_overtime = False

        # Asosiy smena allaqachon bajarilganmi?
        if target_shift:
            main_done = Attendance.objects.filter(
                user=user, shift=target_shift, date=today,
                check_in__isnull=False, is_overtime=False,
            ).exists()

            if main_done:
                # Qo'shimcha smena
                is_overtime = True
        else:
            # Smenasiz hodim — bugun allaqachon tugallangan davomat bormi?
            already_done = Attendance.objects.filter(
                user=user, date=today,
                check_in__isnull=False, check_out__isnull=False,
            ).exists()
            if already_done:
                return JsonResponse({
                    'ok': False,
                    'msg': f'{user.name}, bugungi davomat allaqachon qayd qilingan!'
                }, status=400)

        # Agar overtime bo'lsa va allaqachon overtime ham bo'lsa - ruxsat bermaymiz
        if is_overtime:
            overtime_open = Attendance.objects.filter(
                user=user, date=today, is_overtime=True,
                check_in__isnull=False, check_out__isnull=True,
            ).exists()
            if overtime_open:
                return JsonResponse({
                    'ok': False,
                    'msg': f'{user.name}, sizda ochiq qo\'shimcha smena bor!'
                }, status=400)

        # Yangi davomat yaratish
        att = Attendance.objects.create(
            user=user,
            shift=target_shift,
            branch=user.branch,
            date=today,
            check_in=now,
            status='present',
            is_overtime=is_overtime,
        )

        # Rasmni saqlash
        if photo_file:
            att.photo.save(photo_file.name, photo_file, save=True)

        # Kechikish tekshirish
        if target_shift and target_shift.start_time and not is_overtime:
            shift_start = now.replace(
                hour=target_shift.start_time.hour,
                minute=target_shift.start_time.minute,
                second=0, microsecond=0,
            )
            if now > shift_start:
                att.status = 'late'
                att.save(update_fields=['status'])

        shift_name = target_shift.name if target_shift else ''
        shift_end = ''
        needs_checkout_scan = True
        if target_shift and target_shift.end_time:
            shift_end = target_shift.end_time.strftime('%H:%M')

        overtime_label = ' (Qo\'shimcha)' if is_overtime else ''
        return JsonResponse({
            'ok': True,
            'action': 'check_in',
            'msg': f'{user.name}, xush kelibsiz!{overtime_label}',
            'user_name': user.name,
            'shift': f'{shift_name}{overtime_label}',
            'time': now.strftime('%H:%M'),
            'status': att.get_status_display(),
            'shift_end': shift_end,
            'is_overtime': is_overtime,
            'photo_url': att.photo.url if att.photo else '',
        })

    def _do_checkout(self, user, att, now, photo_file=None):
        """Chiqish qayd qilish."""
        att.check_out = now
        is_early = False

        # Erta ketish tekshirish
        if att.shift and att.shift.end_time:
            shift_end = now.replace(
                hour=att.shift.end_time.hour,
                minute=att.shift.end_time.minute,
                second=0, microsecond=0,
            )
            if now < shift_end:
                is_early = True
                if att.status == 'present':
                    att.status = 'early_leave'

        att.save(update_fields=['check_out', 'status'])

        # Chiqish rasmini saqlash (faqat kirish rasmi bo'lmasa)
        if photo_file and not att.photo:
            att.photo.save(photo_file.name, photo_file, save=True)

        # Ishlagan vaqt
        worked = att.worked_hours_display
        shift_name = att.shift.name if att.shift else ''
        overtime_label = ' (Qo\'shimcha)' if att.is_overtime else ''

        return JsonResponse({
            'ok': True,
            'action': 'check_out',
            'msg': f'{user.name}, sog\'-salomat boring!',
            'user_name': user.name,
            'shift': f'{shift_name}{overtime_label}',
            'time': now.strftime('%H:%M'),
            'worked': worked,
            'is_early': is_early,
            'status': att.get_status_display(),
            'photo_url': att.photo.url if att.photo else '',
        })


# ── Legacy API endpoints (redirect to smart endpoint) ──

@method_decorator(csrf_exempt, name='dispatch')
class CheckInAPIView(AttendanceScanAPIView):
    pass


@method_decorator(csrf_exempt, name='dispatch')
class CheckOutAPIView(AttendanceScanAPIView):
    pass
