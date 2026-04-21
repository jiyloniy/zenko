

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
from apps.users.models import User, Shift

logger = logging.getLogger(__name__)

# ─── sozlamalar ───────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN  = '8723846245:AAFMLFT1gyYIh0FYfBJN-AOCmXcWf49l6pg'
TELEGRAM_CHANNEL_ID = -1003457723502

# Smena boshlanishidan bu daqiqa ichida kelish — "vaqtida" hisoblanadi
LATE_GRACE_MINUTES = 15

# Smena tugashidan keyin bu daqiqa ichida skanerlash —
# check_out = smena end_time yoziladi (kiyim almashish vaqti)
CHECKOUT_GRACE_MINUTES = 30

# ── SMART SHIFT DETECTION ────────────────────────────────────────────────────
# Hodim o'z smenasidan boshqa smenaga kelishi mumkin (masalan, kunduzgi hodim
# kechki smenaga keldi). Quyidagi oyna kenglik doirasida kelish vaqti qaysi
# smenaga to'g'ri kelsa — o'sha smena "effective" sifatida tanlanadi.
#
#   start_time - BEFORE ≤ arrival ≤ start_time + AFTER  →  shu smenaga kelgan
SHIFT_MATCH_BEFORE_MIN = 120   # smena start_time dan shuncha daqiqa oldin (erta kelish)
SHIFT_MATCH_AFTER_MIN  = 240   # smena start_time dan shuncha daqiqa keyin (kechikib kelish)


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


# ══════════════════════════════════════════════════════════════════════════════
# SMART SHIFT DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _available_shifts_for(user):
    """
    Hodim uchun 'mumkin bo'lgan smenalar' ro'yxati:
      - filialdagi barcha smenalar (agar filial bor)
      - + hodimning o'z smenasi (agar ro'yxatda yo'q bo'lsa)

    MUHIM: agar hodimning filiali ham, o'z smenasi ham bo'lmasa — bo'sh ro'yxat
    qaytaramiz. Global (filialsiz) smenalar bilan adashtirmaslik uchun,
    ular faqat hodim o'z smenasi yoki filiali bo'lganda ko'riladi.
    """
    shifts: list = []
    seen_ids: set = set()

    if user.branch_id:
        branch_shifts = Shift.objects.filter(branch_id=user.branch_id)
        for s in branch_shifts:
            if s.start_time and s.end_time:
                shifts.append(s)
                seen_ids.add(s.pk)

    own = getattr(user, 'shift', None)
    if own and own.pk not in seen_ids and own.start_time and own.end_time:
        shifts.append(own)
        seen_ids.add(own.pk)

    return shifts


def _candidate_start_dts(shift, ref_date):
    """
    Smena uchun `ref_date` atrofidagi start_time datetime'larini qaytaradi
    (kecha, bugun, ertaga). Tungi smenalar kecha boshlanib bugun tugashi mumkin.
    """
    dts: list[datetime] = []
    for delta in (-1, 0, 1):
        d = ref_date + timedelta(days=delta)
        sdt = _shift_start_dt(shift, d)
        if sdt:
            dts.append(sdt)
    return dts


def _detect_effective_shift(user, arrival: datetime):
    """
    Hodim kelish vaqti (`arrival`) asosida QAYSI smenaga kelganini aniqlaydi.

    Qaytaradi: (shift_obj, shift_start_dt, shift_end_dt) yoki (None, None, None)

    Algoritm:
      1) Filialdagi barcha smenalarni ko'rib chiqadi.
      2) Har bir smena uchun kecha/bugun/ertaga start_time datetime'lari hisoblanadi.
      3) Arrival ga eng yaqin bo'lgani tanlanadi, lekin:
         - start_time - SHIFT_MATCH_BEFORE_MIN ≤ arrival ≤ start_time + SHIFT_MATCH_AFTER_MIN
           oynasi ichida bo'lishi kerak.
      4) Agar hech biri oynaga tushmasa — hodimning o'z smenasi (bor bo'lsa).
    """
    shifts = _available_shifts_for(user)
    if not shifts:
        return None, None, None

    local_arrival = timezone.localtime(arrival)
    ref_date = local_arrival.date()

    best = None  # (abs_diff_seconds, shift, start_dt)
    for sh in shifts:
        for sdt in _candidate_start_dts(sh, ref_date):
            diff_sec = (local_arrival - timezone.localtime(sdt)).total_seconds()
            # Oyna ichida bo'lishi kerak
            if -SHIFT_MATCH_BEFORE_MIN * 60 <= diff_sec <= SHIFT_MATCH_AFTER_MIN * 60:
                score = abs(diff_sec)
                if best is None or score < best[0]:
                    best = (score, sh, sdt)

    if best is not None:
        _score, shift, start_dt = best
        end_dt = _shift_end_dt_from_start(shift, start_dt)
        return shift, start_dt, end_dt

    # Oynaga tushmadi — o'z smenasiga qaytaramiz (bor bo'lsa)
    own = getattr(user, 'shift', None)
    if own and own.start_time and own.end_time:
        own_start = _shift_start_dt(own, ref_date)
        own_end   = _shift_end_dt_from_start(own, own_start) if own_start else None
        return own, own_start, own_end

    return None, None, None


def _shift_end_dt_from_start(shift, start_dt: datetime | None) -> datetime | None:
    """
    Smena boshlanish datetime'iga qarab tugash datetime'ini qaytaradi.
    Tungi smena (end < start) → ertasi kunga o'tkazadi.
    """
    if not shift or not shift.end_time or not start_dt:
        return None
    tz = timezone.get_current_timezone()
    end_dt = timezone.make_aware(
        datetime.combine(timezone.localtime(start_dt).date(), shift.end_time), tz
    )
    if shift.start_time and shift.end_time <= shift.start_time:
        end_dt += timedelta(days=1)
    return end_dt


def _compute_check_in_info(actual_in: datetime, start_dt: datetime | None) -> dict:
    """
    Kirish vaqtini smena boshlanishiga (`start_dt`) nisbatan tahlil qiladi.

    Qaytaradi:
        effective_in  — pul hisobida ishlatiladigan vaqt
        status        — 'early' | 'present' | 'late'
        diff_minutes  — smena start dan farq (musbat = kech, manfiy = erta)
        note          — Telegram uchun qisqa izoh
    """
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


def _compute_check_out_info(actual_out: datetime, end_dt: datetime | None) -> dict:
    """
    Chiqish vaqtini smena tugashiga (`end_dt`) nisbatan tahlil qiladi.

    Qaytaradi:
        effective_out  — pul hisobida ishlatiladigan vaqt
        early_leave    — True/False (erta chiqish)
        diff_minutes   — smena end dan farq (musbat = kech, manfiy = erta)
        note           — Telegram uchun qisqa izoh
    """
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
    """
    Oldingi kunlarning ochiq yozuvlarini avtomatik yopadi.

    MUHIM: Tungi smena hodimi kecha kechqurun kirishi mumkin (att.date = kecha),
    lekin haqiqiy chiqishi bugun ertalab bo'ladi. Shuning uchun faqat
    att.date < today tekshiruvi yetarli emas — tungi smenaning mumkin bo'lgan
    tugash vaqtini ham hisobga olish kerak.

    Qoida: agar check_in + 14 soat < now bo'lsa — bu haqiqatan ham "eskirgan"
    yozuv deb hisoblanadi va smena tugash vaqtiga yopiladi.
    """
    open_qs = Attendance.objects.filter(
        user=user,
        check_in__isnull=False,
        check_out__isnull=True,
    ).select_related('effective_shift')

    for att in open_qs:
        if not att.check_in:
            continue

        # Tungi smena: check_in + max_shift_duration (14 soat) o'tganmi?
        # 14 soat = eng uzun mumkin smena + bufer. Agar shu vaqt o'tmagan bo'lsa
        # hodim hali tungi smenada ishlayapti deb hisoblaymiz.
        max_shift_hours = timedelta(hours=14)
        if now - att.check_in < max_shift_hours:
            # Hali smena tugash vaqti o'tmagan — tegilmaydi
            continue

        # Smena tugash vaqtiga yopamiz (agar effective_shift bor bo'lsa)
        eff_shift = att.effective_shift
        if eff_shift and eff_shift.start_time and eff_shift.end_time:
            start_dt = _shift_start_dt(eff_shift, att.date)
            end_dt = _shift_end_dt_from_start(eff_shift, start_dt)
            if end_dt:
                att.check_out = end_dt
                att.save(update_fields=['check_out'])
                logger.info(
                    "Auto-checkout (smena end): user=%s date=%s checkout=%s",
                    user.pk, att.date, end_dt,
                )
                continue

        # effective_shift yo'q — check_in sanasining 23:59 ga yopamiz
        tz = timezone.get_current_timezone()
        eod = timezone.make_aware(
            datetime.combine(att.date, datetime.strptime('23:59', '%H:%M').time()), tz
        )
        att.check_out = eod
        att.save(update_fields=['check_out'])
        logger.info("Auto-checkout (23:59): user=%s date=%s", user.pk, att.date)


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

def _shift_range_str(shift) -> str:
    if shift and shift.start_time and shift.end_time:
        return f'{shift.start_time:%H:%M}–{shift.end_time:%H:%M}'
    return '—'


def _tg_checkin_message(
    user,
    attendance: Attendance,
    actual_in: datetime,
    effective_in: datetime,
    status: str,
    diff_minutes: int,
    note: str,
    effective_shift=None,
) -> str:
    """
    Kirish xabari:

    🟢 KIRISH — Alisher Karimov
    ━━━━━━━━━━━━━━━━━━━━━━━━━
    👤 Hodim:      Alisher Karimov
    🏢 Filial:     Chilonzor
    🔧 Bo'lim:     IT
    📌 Yozilgan:   Kunduzgi (08:30–18:30)
    ⏰ Keldi:      Kechki (17:00–02:00)   ← boshqa smenaga kelgan bo'lsa

    🕐 Keldi:      16:45
    ✅ Hisob:      17:00  ← smena boshidan (erta keldi)
    📋 Holat:      ⬆ Smenadan 15 daqiqa oldin keldi

    💡 Ish vaqti smena boshlanishidan hisoblanadi.
    📅 Sana:       12.04.2025
    """
    assigned_shift = getattr(user, 'shift', None)
    # Agar effective_shift ko'rsatilmagan bo'lsa — assigned shift dan foydalanamiz
    eff_shift = effective_shift or assigned_shift

    branch_name   = user.branch.name       if user.branch      else '—'
    dept_name     = user.department.name   if user.department  else '—'
    assigned_name = assigned_shift.name    if assigned_shift   else '—'
    assigned_rng  = _shift_range_str(assigned_shift)
    eff_name      = eff_shift.name         if eff_shift        else '—'
    eff_rng       = _shift_range_str(eff_shift)

    # Hodim o'z smenasiga kelganmi yoki boshqasigami
    shift_mismatch = (
        assigned_shift and eff_shift and assigned_shift.pk != eff_shift.pk
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

    if shift_mismatch:
        shift_block = (
            f"📌 <b>Yozilgan:</b>  {_esc(assigned_name)} ({_esc(assigned_rng)})\n"
            f"🔀 <b>Keldi:</b>     {_esc(eff_name)} ({_esc(eff_rng)})"
            f"  <i>← boshqa smenaga</i>\n"
        )
    else:
        shift_block = f"⏰ <b>Smena:</b>     {_esc(eff_name)} ({_esc(eff_rng)})\n"

    return (
        f"🟢 <b>KIRISH</b> — <b>{_esc(user.name)}</b>\n"
        f"{'━' * 28}\n"
        f"👤 <b>Hodim:</b>     {_esc(user.name)}\n"
        f"🏢 <b>Filial:</b>    {_esc(branch_name)}\n"
        f"🔧 <b>Bo'lim:</b>    {_esc(dept_name)}\n"
        f"{shift_block}"
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
    effective_shift=None,
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
    assigned_shift = getattr(user, 'shift', None)
    eff_shift = effective_shift or assigned_shift

    branch_name   = user.branch.name      if user.branch     else '—'
    assigned_name = assigned_shift.name   if assigned_shift  else '—'
    assigned_rng  = _shift_range_str(assigned_shift)
    eff_name      = eff_shift.name        if eff_shift       else '—'
    eff_rng       = _shift_range_str(eff_shift)

    shift_mismatch = (
        assigned_shift and eff_shift and assigned_shift.pk != eff_shift.pk
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
    elif diff_minutes > CHECKOUT_GRACE_MINUTES:
        holat = f'ℹ️ Smenadan {diff_minutes} daqiqa keyin chiqdi'
        hisob_note = ''
    else:
        holat = _esc(note) if note else '—'
        hisob_note = ''

    if shift_mismatch:
        shift_block = (
            f"📌 <b>Yozilgan:</b>  {_esc(assigned_name)} ({_esc(assigned_rng)})\n"
            f"🔀 <b>Smena:</b>     {_esc(eff_name)} ({_esc(eff_rng)})"
            f"  <i>← boshqa smenaga kelgan edi</i>\n"
        )
    else:
        shift_block = f"⏰ <b>Smena:</b>     {_esc(eff_name)} ({_esc(eff_rng)})\n"

    return (
        f"🔴 <b>CHIQISH</b> — <b>{_esc(user.name)}</b>\n"
        f"{'━' * 28}\n"
        f"👤 <b>Hodim:</b>     {_esc(user.name)}\n"
        f"🏢 <b>Filial:</b>    {_esc(branch_name)}\n"
        f"{shift_block}"
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

def notify_checkin(user, attendance, actual_in, effective_in, status, diff_minutes, note, photo_bytes, effective_shift=None):
    msg = _tg_checkin_message(
        user, attendance, actual_in, effective_in, status, diff_minutes, note,
        effective_shift=effective_shift,
    )
    _tg_send(msg, photo_bytes)


def notify_checkout(user, attendance, actual_out, effective_out, effective_in, early_leave, diff_minutes, note, photo_bytes, effective_shift=None):
    msg = _tg_checkout_message(
        user, attendance, actual_out, effective_out, effective_in, early_leave, diff_minutes, note,
        effective_shift=effective_shift,
    )
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

        # ── 4a. Ochiq yozuv → CHECK-OUT ──────────────────────────────────────
        # MUHIM: Tungi smena hodimi kecha kirgan bo'lishi mumkin (att.date = kecha),
        # shuning uchun faqat bugungi yozuvlarni emas, BARCHA ochiq yozuvlarni
        # tekshiramiz. auto_checkout_expired dan OLDIN qilishimiz kerak — aks holda
        # tungi smena yozuvi 14 soat o'tmagan bo'lsa ham "yopilishi" mumkin edi.
        open_att = (
            Attendance.objects.filter(
                user=user,
                check_in__isnull=False,
                check_out__isnull=True,
            )
            .order_by('check_in', 'id')
            .first()
        )
        if open_att:
            return self._do_checkout(open_att, user, branch, now, photo_bytes)

        auto_checkout_expired(user, now)

        qs = _today_rows(user, today)

        # ── 4b. Bugun allaqachon yopilgan → 409 ──────────────────────────────
        # (disabled — admin vaqtni qayta tahrirlashi mumkin, yoki ikkinchi smena)

        # ── 4c. 'absent' yozuvi bor → CHECK-IN (yangilanadi) ─────────────────
        absent_row = (
            qs.filter(status=Attendance.STATUS_ABSENT, check_in__isnull=True)
            .order_by('id')
            .first()
        )
        if absent_row:
            return self._do_checkin(absent_row, user, branch, now, photo_bytes)

        # ── 4d. Yangi CHECK-IN ────────────────────────────────────────────────
        att = Attendance(user=user, branch=branch, date=today)
        att.save()
        return self._do_checkin(att, user, branch, now, photo_bytes)

    # ─────────────────────────────────────────────────────────────────────────
    def _do_checkin(self, att, user, branch, now, photo_bytes):
        """
        Check-in mantiqi.

        Smart shift detection: hodim kelish vaqtiga qarab, uning filialidagi
        barcha smenalardan eng mos keladiganini topadi. Shunda kunduzgi smenaga
        yozilgan hodim kechki smenaga kelganda ham to'g'ri hisoblanadi.
        """
        actual_in = now
        eff_shift, start_dt, _end_dt = _detect_effective_shift(user, actual_in)

        info = _compute_check_in_info(actual_in=actual_in, start_dt=start_dt)

        att.check_in            = actual_in
        att.effective_check_in  = info['effective_in']
        att.check_out           = None
        att.actual_check_out    = None
        att.effective_shift     = eff_shift
        # 'early' statusini 'present' sifatida saqlaymiz (Telegram ga 'early' boradi)
        att.status              = info['status'] if info['status'] != 'early' else Attendance.STATUS_PRESENT
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
            effective_shift=eff_shift,
        )

        shift_data = self._shift_payload(eff_shift)

        return JsonResponse({
            'ok':            True,
            'action':        'check_in',
            'msg':           f"{user.name} kirdi",
            'user_name':     user.name,
            'time':          _fmt_time(actual_in),
            'hisob_time':    _fmt_time(info['effective_in']),
            'is_early':      info['status'] == 'early',
            'is_late':       info['status'] == Attendance.STATUS_LATE,
            'diff_minutes':  info['diff_minutes'],
            'status':        att.status,
            'shift_matched': bool(eff_shift and user.shift_id and eff_shift.pk != user.shift_id),
            **shift_data,
        })

    # ─────────────────────────────────────────────────────────────────────────
    def _do_checkout(self, open_att, user, branch, now, photo_bytes):
        """
        Check-out mantiqi.

        Check-in da saqlangan `effective_shift` ishlatiladi — shunda
        hodim kunduzgi smenaga yozilgan bo'lsa ham, kechki smenaga kelgan
        bo'lsa, kechki smena bo'yicha chiqish hisoblanadi.
        """
        actual_out = now

        # Saqlangan effective_shift → uning end_dt ini check_in sanasi va
        # start_time asosida qayta hisoblaymiz (tungi smena uchun muhim).
        #
        # MUHIM: check_in vaqtidan start_dt ni aniqlaymiz, open_att.date dan emas.
        # Sabab: tungi smena hodimi 20.04 da kirdi (check_in = 20.04 20:14),
        # 21.04 da chiqdi. open_att.date = 20.04. Lekin _shift_start_dt(shift, 20.04)
        # → 20.04 20:00 → end = 21.04 05:00. Bu to'g'ri.
        # Agar check_in o'zidan boshqa sanaga tushsa (masalan, tungi smenada)
        # check_in lokalvaqti asosida start_dt ni qidiramiz.
        eff_shift = open_att.effective_shift
        end_dt = None
        if eff_shift and eff_shift.start_time and eff_shift.end_time:
            # check_in lokal sanasiga qarab start_dt topamiz — bu tungi smenada to'g'ri ishlaydi
            check_in_local_date = timezone.localtime(open_att.check_in).date() if open_att.check_in else open_att.date
            start_dt = _shift_start_dt(eff_shift, check_in_local_date)
            end_dt = _shift_end_dt_from_start(eff_shift, start_dt)

        info = _compute_check_out_info(actual_out=actual_out, end_dt=end_dt)

        effective_in = open_att.effective_check_in or open_att.check_in

        open_att.check_out        = info['effective_out']
        open_att.actual_check_out = actual_out
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
            effective_shift=eff_shift,
        )

        worked_seconds = 0
        if effective_in and info['effective_out']:
            worked_seconds = max(0, int((info['effective_out'] - effective_in).total_seconds()))

        shift_data = self._shift_payload(eff_shift)

        return JsonResponse({
            'ok':            True,
            'action':        'check_out',
            'msg':           f"{user.name} chiqdi",
            'user_name':     user.name,
            'time':          _fmt_time(actual_out),
            'hisob_time':    _fmt_time(info['effective_out']),
            'worked':        _fmt_duration(worked_seconds),
            'early_leave':   info['early_leave'],
            'status':        open_att.status,
            'shift_matched': bool(eff_shift and user.shift_id and eff_shift.pk != user.shift_id),
            **shift_data,
        })

    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _shift_payload(shift) -> dict:
        """Frontend uchun smena ma'lumotlari."""
        return {
            'shift_name':  shift.name                          if shift else '',
            'shift_start': shift.start_time.strftime('%H:%M') if shift and shift.start_time else '',
            'shift_end':   shift.end_time.strftime('%H:%M')   if shift and shift.end_time   else '',
        }


@method_decorator(csrf_exempt, name='dispatch')
class CheckInAPIView(AttendanceScanAPIView):
    pass

@method_decorator(csrf_exempt, name='dispatch')
class CheckOutAPIView(AttendanceScanAPIView):
    pass


