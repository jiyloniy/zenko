"""
apps/attendance/views.py

Davomat logikasi (QR scanner kiosk uchun):

KIRISH:
  - Hodim smena boshlanishidan OLDIN kelsa:
      • check_in = haqiqiy kelish vaqti  (log uchun)
      • effective_check_in = smena start_time  (pul hisobi uchun)
      • status = 'early'
  - Hodim smena boshlanishidan KEYIN kelsa:
      • check_in = haqiqiy kelish vaqti
      • effective_check_in = haqiqiy kelish vaqti
      • status = 'late'
  - Vaqtida kelsa (± grace_minutes):
      • status = 'present'

CHIQISH:
  - Hodim smena tugashidan keyin 0–30 daqiqa ichida skanerlasa:
      • check_out = smena end_time  (pul hisobi uchun)
      • actual_check_out = haqiqiy chiqish vaqti  (log uchun)
  - 30 daqiqadan keyin (kech qolsa):
      • check_out = haqiqiy chiqish vaqti
  - Smena tugashidan OLDIN chiqsa:
      • check_out = haqiqiy chiqish vaqti
      • status uchun 'early_leave' belgisi

TELEGRAM:
  - Har bir hodim uchun batafsil, emoji-li xabar yuboriladi.
"""

from __future__ import annotations

import base64
import io
import logging
from datetime import datetime, timedelta

import qrcode
from qrcode.constants import ERROR_CORRECT_H
import requests
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.attendance.models import Attendance
from apps.users.models import User

logger = logging.getLogger(__name__)

# ─── sozlamalar ───────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN  = '8723846245:AAFMLFT1gyYIh0FYfBJN-AOCmXcWf49l6pg'
TELEGRAM_CHANNEL_ID = -1003457723502

# Smena boshlanishidan bu daqiqa ichida kelish — "vaqtida" hisoblanadi
LATE_GRACE_MINUTES = 15

# Smena tugashidan keyin bu daqiqa ichida skanerlash —
# check_out = smena end_time yoziladi (kiyim almashish vaqti)
CHECKOUT_GRACE_MINUTES = 30 


# ══════════════════════════════════════════════════════════════════════════════
# QR TOKEN
# ══════════════════════════════════════════════════════════════════════════════

def generate_qr_token(user) -> str:
    """Token = user.pk string ko'rinishida. Hardware scanner uchun oddiy raqam."""
    return str(user.pk)


def verify_qr_token(token: str):
    """Token → User yoki None. Strip qilinadi (scanner \n qo'shishi mumkin)."""
    if not token:
        return None
    token = token.strip()
    try:
        user_id = int(token)
    except (ValueError, TypeError):
        logger.warning("verify_qr_token: invalid token %r", token)
        return None

    user = (
        User.objects
        .filter(pk=user_id, is_active=True)
        .select_related('branch', 'shift')
        .first()
    )
    if not user:
        logger.warning("verify_qr_token: user pk=%s not found or inactive", user_id)
    return user


# ══════════════════════════════════════════════════════════════════════════════
# SHIFT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _shift_start_dt(shift, date) -> datetime | None:
    """Smena boshlanish vaqtini aware datetime sifatida qaytaradi."""
    if not shift or not shift.start_time:
        return None
    tz = timezone.get_current_timezone()
    return timezone.make_aware(
        datetime.combine(date, shift.start_time), tz
    )


def _shift_end_dt(shift, date) -> datetime | None:
    """
    Smena tugash vaqtini aware datetime sifatida qaytaradi.
    Tungi smena uchun (end < start) — ertasi kunga o'tkazadi.
    """
    if not shift or not shift.end_time:
        return None
    tz = timezone.get_current_timezone()
    end_dt = timezone.make_aware(
        datetime.combine(date, shift.end_time), tz
    )
    # Tungi smena: end_time < start_time → ertasi kun
    if shift.start_time and shift.end_time < shift.start_time:
        end_dt += timedelta(days=1)
    return end_dt


def _compute_check_in_info(actual_in: datetime, shift) -> dict:
    """
    Kirish vaqtini shift ga nisbatan tahlil qiladi.

    Qaytaradi:
        effective_in  — pul hisobida ishlatilادیgan vaqt
        status        — 'early' | 'present' | 'late'
        diff_minutes  — smena start dan farq (musbat = kech, manfiy = erta)
        note          — Telegram uchun qisqa izoh
    """
    if not shift or not shift.start_time:
        return {
            'effective_in': actual_in,
            'status': Attendance.STATUS_PRESENT,
            'diff_minutes': 0,
            'note': '',
        }

    date = timezone.localtime(actual_in).date()
    start_dt = _shift_start_dt(shift, date)
    if not start_dt:
        return {
            'effective_in': actual_in,
            'status': Attendance.STATUS_PRESENT,
            'diff_minutes': 0,
            'note': '',
        }

    diff = int((timezone.localtime(actual_in) - timezone.localtime(start_dt)).total_seconds() / 60)
    # diff < 0  → erta keldi
    # diff == 0..LATE_GRACE_MINUTES → vaqtida
    # diff > LATE_GRACE_MINUTES → kech

    if diff < 0:
        # Erta keldi: hisob smena boshidan
        return {
            'effective_in': start_dt,
            'status': 'early',
            'diff_minutes': diff,
            'note': f'Smenadan {abs(diff)} daqiqa oldin keldi',
        }
    elif diff <= LATE_GRACE_MINUTES:
        return {
            'effective_in': actual_in,
            'status': Attendance.STATUS_PRESENT,
            'diff_minutes': diff,
            'note': 'Vaqtida keldi' if diff == 0 else f'{diff} daqiqa kechikdi (chegara ichida)',
        }
    else:
        return {
            'effective_in': actual_in,
            'status': Attendance.STATUS_LATE,
            'diff_minutes': diff,
            'note': f'{diff} daqiqa kechikdi',
        }


def _compute_check_out_info(actual_out: datetime, shift, check_in_date) -> dict:
    """
    Chiqish vaqtini shift ga nisbatan tahlil qiladi.

    Qaytaradi:
        effective_out  — pul hisobida ishlatilادیgan vaqt
        early_leave    — True/False (erta chiqish)
        diff_minutes   — smena end dan farq (musbat = kech, manfiy = erta)
        note           — Telegram uchun qisqa izoh
    """
    if not shift or not shift.end_time:
        return {
            'effective_out': actual_out,
            'early_leave': False,
            'diff_minutes': 0,
            'note': '',
        }

    end_dt = _shift_end_dt(shift, check_in_date)
    if not end_dt:
        return {
            'effective_out': actual_out,
            'early_leave': False,
            'diff_minutes': 0,
            'note': '',
        }

    diff = int((timezone.localtime(actual_out) - timezone.localtime(end_dt)).total_seconds() / 60)
    # diff < 0  → erta chiqdi
    # 0 ≤ diff ≤ CHECKOUT_GRACE_MINUTES → smena tugagach kiyim almashtirdi
    # diff > CHECKOUT_GRACE_MINUTES → kech qoldi (o'z xohishi bilan)

    if diff < 0:
        # Erta chiqish: haqiqiy vaqt yoziladi
        return {
            'effective_out': actual_out,
            'early_leave': True,
            'diff_minutes': diff,
            'note': f'Smenadan {abs(diff)} daqiqa oldin chiqdi',
        }
    elif diff <= CHECKOUT_GRACE_MINUTES:
        # Grace period: smena end_time yoziladi (kiyim almashish)
        return {
            'effective_out': end_dt,
            'early_leave': False,
            'diff_minutes': diff,
            'note': f'Smenadan {diff} daqiqa keyin skanerladi → smena tugash vaqti yozildi',
        }
    else:
        # Ancha kech: haqiqiy vaqt yoziladi
        return {
            'effective_out': actual_out,
            'early_leave': False,
            'diff_minutes': diff,
            'note': f'Smenadan {diff} daqiqa keyin chiqdi',
        }


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _branch_matches(user, kiosk_branch_id) -> tuple[bool, str]:
    if not user.branch_id:
        return False, 'Hodimga filial biriktirilmagan'
    if not kiosk_branch_id:
        return False, 'Kiosk filiali tanlanmagan'
    try:
        kb = int(kiosk_branch_id)
    except (ValueError, TypeError):
        return False, "Noto'g'ri filial ID"
    if user.branch_id != kb:
        return False, f'Bu QR boshqa filial uchun ({user.branch.name})'
    return True, ''


def auto_checkout_expired(user, now):
    """Oldingi kunlarning ochiq yozuvlarini 23:59 da yopadi."""
    today = now.date()
    open_qs = Attendance.objects.filter(
        user=user,
        check_in__isnull=False,
        check_out__isnull=True,
    )
    for att in open_qs:
        if att.date < today and att.check_in:
            att.check_out = att.check_in.replace(
                hour=23, minute=59, second=0, microsecond=0
            )
            att.save(update_fields=['check_out'])
            logger.info("Auto-checkout: user=%s date=%s", user.pk, att.date)


def _decode_photo_data(photo_raw: str) -> bytes | None:
    """Base64 data-URL → bytes."""
    if not photo_raw:
        return None
    if photo_raw.startswith('data:image'):
        try:
            _header, b64 = photo_raw.split(',', 1)
            return base64.b64decode(b64)
        except Exception as e:
            logger.warning("Photo decode error: %s", e)
            return None
    try:
        return base64.b64decode(photo_raw)
    except Exception:
        return None


def _save_attendance_photo(attendance, photo_bytes: bytes | None):
    if not photo_bytes:
        return
    try:
        fname = f'{attendance.user_id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        attendance.photo.save(fname, ContentFile(photo_bytes), save=True)
    except Exception as e:
        logger.warning("Photo save error: %s", e)


def _today_rows(user, today):
    return Attendance.objects.filter(user=user, date=today)


def _fmt_time(dt) -> str:
    """Aware datetime → '08:30' local time."""
    if not dt:
        return '—'
    return timezone.localtime(dt).strftime('%H:%M')


def _fmt_duration(seconds: int) -> str:
    """Sekundlar → '8 soat 25 daqiqa'."""
    if seconds <= 0:
        return '0 daqiqa'
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h and m:
        return f'{h} soat {m} daqiqa'
    elif h:
        return f'{h} soat'
    return f'{m} daqiqa'


# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM  — chiroyli, batafsil xabarlar
# ══════════════════════════════════════════════════════════════════════════════

def _esc(text: str) -> str:
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _tg_post(url: str, data: dict, files=None, timeout: int = 8):
    try:
        resp = requests.post(
            url,
            data=data,
            files=files,
            timeout=timeout,
        )
        if not resp.ok:
            logger.warning("Telegram API error: %s %s", resp.status_code, resp.text[:300])
    except requests.RequestException as e:
        logger.warning("Telegram send failed: %s", e)


def _tg_send(caption: str, photo_bytes: bytes | None):
    """Telegram ga rasm yoki matn yuboradi."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    base = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    if photo_bytes:
        _tg_post(
            f"{base}/sendPhoto",
            {"chat_id": TELEGRAM_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("photo.jpg", photo_bytes, "image/jpeg")},
        )
    else:
        _tg_post(
            f"{base}/sendMessage",
            {"chat_id": TELEGRAM_CHANNEL_ID, "text": caption, "parse_mode": "HTML"},
        )


# ─── xabar quriluvchilari ─────────────────────────────────────────────────────

def _tg_checkin_message(
    user,
    attendance: Attendance,
    actual_in: datetime,
    effective_in: datetime,
    status: str,
    diff_minutes: int,
    note: str,
) -> str:
    """
    Kirish xabari:

    🟢 KIRISH — Alisher Karimov
    ━━━━━━━━━━━━━━━━━━━━━━━━━
    👤 Hodim:      Alisher Karimov
    🏢 Filial:     Chilonzor
    🔧 Bo'lim:     IT
    ⏰ Smena:      Kunduzgi (08:30–18:30)

    🕐 Keldi:      07:45
    ✅ Hisob:      08:30  ← smena boshidan (erta keldi)
    📋 Holat:      ⬆ Smenadan 45 daqiqa oldin keldi

    💡 Ish vaqti smena boshlanishidan hisoblanadi.
    📅 Sana:       12.04.2025
    """
    shift = user.shift
    branch_name  = user.branch.name       if user.branch      else '—'
    dept_name    = user.department.name   if user.department  else '—'
    shift_name   = shift.name             if shift            else '—'
    shift_range  = (
        f'{shift.start_time:%H:%M}–{shift.end_time:%H:%M}'
        if shift and shift.start_time and shift.end_time else '—'
    )

    status_line = {
        'early':   f'⬆️ Smenadan {abs(diff_minutes)} daqiqa oldin keldi',
        'present': '✅ Vaqtida keldi',
        'late':    f'⚠️ {diff_minutes} daqiqa kechikdi',
    }.get(status, _esc(note))

    effective_note = ''
    if status == 'early':
        effective_note = '\n💡 <i>Ish vaqti smena boshlanishidan hisoblanadi.</i>'
    elif status == 'late':
        effective_note = '\n💡 <i>Kechikish davomati hisobiga kiradi.</i>'

    return (
        f"🟢 <b>KIRISH</b> — <b>{_esc(user.name)}</b>\n"
        f"{'━' * 28}\n"
        f"👤 <b>Hodim:</b>     {_esc(user.name)}\n"
        f"🏢 <b>Filial:</b>    {_esc(branch_name)}\n"
        f"🔧 <b>Bo'lim:</b>    {_esc(dept_name)}\n"
        f"⏰ <b>Smena:</b>     {_esc(shift_name)} ({_esc(shift_range)})\n"
        f"\n"
        f"🕐 <b>Keldi:</b>     {_fmt_time(actual_in)}\n"
        f"✅ <b>Hisob:</b>     {_fmt_time(effective_in)}\n"
        f"📋 <b>Holat:</b>     {status_line}"
        f"{effective_note}\n"
        f"\n"
        f"📅 <b>Sana:</b>      {attendance.date.strftime('%d.%m.%Y')}"
    )


def _tg_checkout_message(
    user,
    attendance: Attendance,
    actual_out: datetime,
    effective_out: datetime,
    effective_in: datetime,
    early_leave: bool,
    diff_minutes: int,
    note: str,
) -> str:
    """
    Chiqish xabari:

    🔴 CHIQISH — Alisher Karimov
    ━━━━━━━━━━━━━━━━━━━━━━━━━
    👤 Hodim:      Alisher Karimov
    🏢 Filial:     Chilonzor
    ⏰ Smena:      Kunduzgi (08:30–18:30)

    🕘 Chiqdi:     18:47
    ✅ Hisob:      18:30  ← smena tugash vaqti (grace period)
    ⏱ Ishladi:    9 soat 55 daqiqa  (hisob bo'yicha)
    📋 Holat:      Smenadan 17 daqiqa keyin → smena vaqti yozildi
    """
    shift = user.shift
    branch_name = user.branch.name      if user.branch     else '—'
    shift_name  = shift.name            if shift           else '—'
    shift_range = (
        f'{shift.start_time:%H:%M}–{shift.end_time:%H:%M}'
        if shift and shift.start_time and shift.end_time else '—'
    )

    # Hisob bo'yicha ishlagan vaqt
    worked_seconds = 0
    if effective_in and effective_out:
        delta = effective_out - effective_in
        worked_seconds = max(0, int(delta.total_seconds()))

    worked_str = _fmt_duration(worked_seconds)

    if early_leave:
        holat = f'⚠️ Smenadan {abs(diff_minutes)} daqiqa oldin chiqdi'
        hisob_note = '\n💡 <i>Erta chiqish — haqiqiy vaqt yozildi.</i>'
    elif 0 <= diff_minutes <= CHECKOUT_GRACE_MINUTES:
        holat = f'✅ Smena tugadi (+{diff_minutes} daqiqa — kiyim almashish)'
        hisob_note = '\n💡 <i>Smena tugash vaqti hisobga olindi.</i>'
    else:
        holat = f'ℹ️ Smenadan {diff_minutes} daqiqa keyin chiqdi'
        hisob_note = ''

    return (
        f"🔴 <b>CHIQISH</b> — <b>{_esc(user.name)}</b>\n"
        f"{'━' * 28}\n"
        f"👤 <b>Hodim:</b>     {_esc(user.name)}\n"
        f"🏢 <b>Filial:</b>    {_esc(branch_name)}\n"
        f"⏰ <b>Smena:</b>     {_esc(shift_name)} ({_esc(shift_range)})\n"
        f"\n"
        f"🕘 <b>Chiqdi:</b>    {_fmt_time(actual_out)}\n"
        f"✅ <b>Hisob:</b>     {_fmt_time(effective_out)}\n"
        f"⏱ <b>Ishladi:</b>   {_esc(worked_str)} <i>(hisob bo'yicha)</i>\n"
        f"📋 <b>Holat:</b>     {holat}"
        f"{hisob_note}\n"
        f"\n"
        f"📅 <b>Sana:</b>      {attendance.date.strftime('%d.%m.%Y')}"
    )


def _tg_error_message(user_name: str | None, error_msg: str) -> str:
    name = _esc(user_name or "Noma'lum")
    return (
        f"❌ <b>XATOLIK</b>\n"
        f"{'━' * 28}\n"
        f"👤 <b>Foydalanuvchi:</b> {name}\n"
        f"🚫 <b>Sabab:</b> {_esc(error_msg)}\n"
        f"🕐 <b>Vaqt:</b> {timezone.localtime().strftime('%H:%M')}\n"
        f"📅 <b>Sana:</b> {timezone.localtime().strftime('%d.%m.%Y')}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Asosiy yuboruvchi funksiyalar
# ──────────────────────────────────────────────────────────────────────────────

def notify_checkin(user, attendance, actual_in, effective_in, status, diff_minutes, note, photo_bytes):
    msg = _tg_checkin_message(user, attendance, actual_in, effective_in, status, diff_minutes, note)
    _tg_send(msg, photo_bytes)


def notify_checkout(user, attendance, actual_out, effective_out, effective_in, early_leave, diff_minutes, note, photo_bytes):
    msg = _tg_checkout_message(user, attendance, actual_out, effective_out, effective_in, early_leave, diff_minutes, note)
    _tg_send(msg, photo_bytes)


def notify_error(user_name, error_msg, photo_bytes):
    msg = _tg_error_message(user_name, error_msg)
    _tg_send(msg, photo_bytes)


# ══════════════════════════════════════════════════════════════════════════════
# QR CODE IMAGE VIEW
# ══════════════════════════════════════════════════════════════════════════════

class QRCodeImageView(View):
    """GET /qr/<user_id>/ → PNG rasm."""

    def get(self, request, user_id):
        user  = get_object_or_404(User, pk=user_id, is_active=True)
        token = generate_qr_token(user)

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)

        img = self._make_image(qr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return HttpResponse(buf.getvalue(), content_type='image/png')

    @staticmethod
    def _make_image(qr):
        # 1) Styled (yumaloq modullar)
        try:
            from qrcode.image.styledpil import StyledPilImage
            from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
            from qrcode.image.styles.colormasks import SolidFillColorMask
            return qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                color_mask=SolidFillColorMask(
                    back_color=(255, 255, 255),
                    front_color=(15, 23, 42),
                ),
            )
        except ImportError as e:
            logger.info("StyledPilImage not available (%s), plain QR", e)
        except Exception as e:
            logger.warning("StyledPilImage failed (%s), plain QR", e)

        # 2) Oddiy qora-oq QR
        return qr.make_image(fill_color='#0F172A', back_color='#FFFFFF')


# ══════════════════════════════════════════════════════════════════════════════
# KIOSK PAGE VIEW
# ══════════════════════════════════════════════════════════════════════════════

class AttendanceKioskView(View):
    def get(self, request):
        branch_id   = request.GET.get('branch', '').strip()
        branch_name = ''
        if branch_id.isdigit():
            from apps.users.models import Branch
            b = Branch.objects.filter(pk=int(branch_id)).first()
            if b:
                branch_name = b.name
        return render(request, 'attendance/kiosk.html', {
            'kiosk_branch_id':   branch_id if branch_id.isdigit() else '',
            'kiosk_branch_name': branch_name,
        })


class CheckInPageView(AttendanceKioskView):
    pass

class CheckOutPageView(AttendanceKioskView):
    pass


# ══════════════════════════════════════════════════════════════════════════════
# SCAN API  (asosiy logika)
# ══════════════════════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class AttendanceScanAPIView(View):
    """
    POST /api/scan/
    Body (form-urlencoded):
        token      — QR dan o'qilgan matn (user.pk string)
        branch_id  — kiosk filial ID
        photo      — base64 data-URL (ixtiyoriy)
    """

    def post(self, request):
        token        = request.POST.get('token', '').strip()
        kiosk_branch = request.POST.get('branch_id', '').strip()
        photo_raw    = request.POST.get('photo', '').strip()
        photo_bytes  = _decode_photo_data(photo_raw)

        # ── 1. Token bo'sh ───────────────────────────────────────────────────
        if not token:
            notify_error(None, 'Token topilmadi', photo_bytes)
            return JsonResponse({'ok': False, 'msg': 'Token topilmadi'}, status=400)

        # ── 2. Token tekshiruvi ──────────────────────────────────────────────
        user = verify_qr_token(token)
        if not user:
            notify_error(None, "Noto'g'ri yoki eskirgan QR kod", photo_bytes)
            return JsonResponse(
                {'ok': False, 'msg': "Noto'g'ri yoki eskirgan QR kod"},
                status=400,
            )

        # ── 3. Filial tekshiruvi ─────────────────────────────────────────────
        ok_branch, branch_msg = _branch_matches(user, kiosk_branch or None)
        if not ok_branch:
            notify_error(user.name, branch_msg, photo_bytes)
            return JsonResponse({'ok': False, 'msg': branch_msg}, status=400)

        # ── 4. Asosiy mantiq ─────────────────────────────────────────────────
        now    = timezone.localtime()
        today  = now.date()
        branch = user.branch
        shift  = user.shift

        auto_checkout_expired(user, now)

        qs = _today_rows(user, today)

        shift_data = {
            'shift_name':  shift.name                          if shift else '',
            'shift_start': shift.start_time.strftime('%H:%M') if shift and shift.start_time else '',
            'shift_end':   shift.end_time.strftime('%H:%M')   if shift and shift.end_time   else '',
        }

        # ── 4a. Ochiq yozuv → CHECK-OUT ──────────────────────────────────────
        open_att = (
            qs.filter(check_in__isnull=False, check_out__isnull=True)
            .order_by('check_in', 'id')
            .first()
        )
        if open_att:
            actual_out = now
            info = _compute_check_out_info(
                actual_out=actual_out,
                shift=shift,
                check_in_date=open_att.date,
            )

            # effective_in — avval saqlangan bo'lishi kerak
            # Attendance modelida effective_check_in maydoni bor deb faraz qilamiz,
            # yo'q bo'lsa check_in ishlatiladi
            effective_in = getattr(open_att, 'effective_check_in', None) or open_att.check_in

            open_att.check_out           = info['effective_out']
            open_att.actual_check_out    = actual_out            # haqiqiy vaqt
            if branch:
                open_att.branch = branch

            fields = ['check_out', 'actual_check_out']
            if branch:
                fields.append('branch')
            open_att.save(update_fields=fields)

            notify_checkout(
                user=user,
                attendance=open_att,
                actual_out=actual_out,
                effective_out=info['effective_out'],
                effective_in=effective_in,
                early_leave=info['early_leave'],
                diff_minutes=info['diff_minutes'],
                note=info['note'],
                photo_bytes=photo_bytes,
            )

            worked_seconds = 0
            if effective_in and info['effective_out']:
                worked_seconds = max(0, int((info['effective_out'] - effective_in).total_seconds()))

            return JsonResponse({
                'ok':           True,
                'action':       'check_out',
                'msg':          f"{user.name} chiqdi",
                'user_name':    user.name,
                'time':         _fmt_time(actual_out),
                'hisob_time':   _fmt_time(info['effective_out']),
                'worked':       _fmt_duration(worked_seconds),
                'early_leave':  info['early_leave'],
                'status':       open_att.status,
                **shift_data,
            })

        # ── 4b. Bugun allaqachon yopilgan → 409 ──────────────────────────────
        # if qs.filter(check_in__isnull=False, check_out__isnull=False).exists():
        #     return JsonResponse({
        #         'ok':  False,
        #         'msg': 'Bugun davomat allaqachon yopilgan. Admin vaqtni tahrirlashi mumkin.',
        #     }, status=409)

        # ── 4c. 'absent' yozuvi bor → CHECK-IN (yangilanadi) ─────────────────
        absent_row = (
            qs.filter(status=Attendance.STATUS_ABSENT, check_in__isnull=True)
            .order_by('id')
            .first()
        )
        if absent_row:
            return self._do_checkin(
                request, absent_row, user, branch, shift,
                now, photo_bytes, shift_data, is_new=False,
            )

        # ── 4d. Yangi CHECK-IN ────────────────────────────────────────────────
        att = Attendance(user=user, branch=branch, date=today)
        att.save()
        return self._do_checkin(
            request, att, user, branch, shift,
            now, photo_bytes, shift_data, is_new=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    def _do_checkin(self, request, att, user, branch, shift, now, photo_bytes, shift_data, is_new: bool):
        """Check-in mantiqini bir joyga to'plash."""
        actual_in = now
        info = _compute_check_in_info(actual_in=actual_in, shift=shift)

        att.check_in            = actual_in
        att.effective_check_in  = info['effective_in']   # ← smena boshidan hisob
        att.check_out           = None
        att.actual_check_out    = None
        att.status              = info['status'] if info['status'] != 'early' else Attendance.STATUS_PRESENT
        # 'early' statusini 'present' sifatida saqlaymiz (lekin Telegram ga 'early' boramiz)
        if branch:
            att.branch = branch

        att.save()
        _save_attendance_photo(att, photo_bytes)

        notify_checkin(
            user=user,
            attendance=att,
            actual_in=actual_in,
            effective_in=info['effective_in'],
            status=info['status'],
            diff_minutes=info['diff_minutes'],
            note=info['note'],
            photo_bytes=photo_bytes,
        )

        return JsonResponse({
            'ok':           True,
            'action':       'check_in',
            'msg':          f"{user.name} kirdi",
            'user_name':    user.name,
            'time':         _fmt_time(actual_in),
            'hisob_time':   _fmt_time(info['effective_in']),
            'is_early':     info['status'] == 'early',
            'is_late':      info['status'] == Attendance.STATUS_LATE,
            'diff_minutes': info['diff_minutes'],
            'status':       att.status,
            **shift_data,
        })


@method_decorator(csrf_exempt, name='dispatch')
class CheckInAPIView(AttendanceScanAPIView):
    pass

@method_decorator(csrf_exempt, name='dispatch')
class CheckOutAPIView(AttendanceScanAPIView):
    pass