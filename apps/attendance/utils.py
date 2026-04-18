"""Davomat va vaqt bilan bog'liq yordamchilar."""

import datetime
import re

# 24 soat: 00:00 … 23:59 yoki 9:05 (daqiqa har doim 2 raqam)
HHMM_24_RE = re.compile(r'^([01][0-9]|2[0-3]|[0-9]):([0-5][0-9])$')


def parse_time_24h(value):
    """
    Matndan vaqtni olish (faqat 24 soatlik HH:MM).
    Qaytaradi: datetime.time yoki None (bo'sh qiymat).
    """
    if value is None:
        return None
    if isinstance(value, datetime.time):
        return value
    s = str(value).strip()
    if not s:
        return None
    m = HHMM_24_RE.match(s)
    if not m:
        raise ValueError('Vaqt 24 soatlik HH:MM formatida bo\'lishi kerak (masalan 08:30 yoki 17:45).')
    h, mm = int(m.group(1)), int(m.group(2))
    return datetime.time(h, mm)


def format_time_24h(t):
    """datetime.time ni 24 soatlik qatorga (masalan 08:05)."""
    if not t:
        return ''
    return t.strftime('%H:%M')
