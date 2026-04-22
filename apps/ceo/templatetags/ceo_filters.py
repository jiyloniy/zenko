from django import template

register = template.Library()


@register.filter
def hours_to_hm(value):
    """
    Soat (float) ni 'X soat Y daqiqa' formatiga o'tkazadi.
    Masalan: 9.97 → '9 soat 58 daqiqa'
    """
    try:
        total_minutes = round(float(value) * 60)
    except (TypeError, ValueError):
        return '—'
    if total_minutes <= 0:
        return '—'
    h = total_minutes // 60
    m = total_minutes % 60
    if h and m:
        return f'{h} soat {m} daqiqa'
    elif h:
        return f'{h} soat'
    return f'{m} daqiqa'


@register.filter
def seconds_to_hm(value):
    """
    Soniya (float/int) ni 'X soat Y daqiqa' formatiga o'tkazadi.
    """
    try:
        total = int(float(value))
    except (TypeError, ValueError):
        return '—'
    if total <= 0:
        return '—'
    h = total // 3600
    m = (total % 3600) // 60
    if h and m:
        return f'{h} soat {m} daqiqa'
    elif h:
        return f'{h} soat'
    return f'{m} daqiqa'
