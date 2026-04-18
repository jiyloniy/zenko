"""
apps/attendance/models.py

Yangi maydonlar:
  effective_check_in  — pul hisobida ishlatiladigan kirish vaqti
                        (erta kelsa = smena start_time, boshqacha = check_in)
  actual_check_out    — haqiqiy chiqish vaqti (log uchun)
                        (check_out = hisobiy vaqt, actual_check_out = haqiqiy)
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.users.models import Branch


class Attendance(models.Model):
    STATUS_PRESENT = 'present'
    STATUS_LATE    = 'late'
    STATUS_ABSENT  = 'absent'

    STATUS_CHOICES = (
        (STATUS_PRESENT, 'Vaqtida keldi'),
        (STATUS_LATE,    'Kechikdi'),
        (STATUS_ABSENT,  'Kelmadi'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Hodim',
        on_delete=models.CASCADE,
        related_name='attendances',
    )
    branch = models.ForeignKey(
        Branch,
        verbose_name='Filial',
        on_delete=models.PROTECT,
        related_name='attendances',
        null=True,
        blank=True,
    )
    date      = models.DateField('Sana')

    # ── haqiqiy vaqtlar (kiosk skanerlagan vaqt) ────────────────────────────
    check_in  = models.DateTimeField('Kirish vaqti (haqiqiy)',  null=True, blank=True)
    check_out = models.DateTimeField('Chiqish vaqti (hisobiy)', null=True, blank=True)

    # ── hisob uchun vaqtlar ──────────────────────────────────────────────────
    effective_check_in = models.DateTimeField(
        'Kirish vaqti (hisob)',
        null=True, blank=True,
        help_text='Erta kelsa smena start_time, kechiksa/vaqtida check_in vaqti.',
    )
    actual_check_out = models.DateTimeField(
        'Chiqish vaqti (haqiqiy)',
        null=True, blank=True,
        help_text='Kiosk skanerlagan haqiqiy vaqt. check_out = hisobiy (smena end yoki haqiqiy).',
    )

    status = models.CharField(
        'Holat',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PRESENT,
    )
    photo = models.ImageField(
        'Rasm',
        upload_to='attendance_photos/%Y/%m/%d/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Davomat'
        verbose_name_plural = 'Davomatlar'
        ordering            = ['-date', '-check_in']

    def __str__(self):
        return f'{self.user} — {self.date}'

    # ── computed properties ───────────────────────────────────────────────────

    @property
    def billing_check_in(self):
        """Hisob uchun kirish vaqti."""
        return self.effective_check_in or self.check_in

    @property
    def billing_check_out(self):
        """Hisob uchun chiqish vaqti."""
        return self.check_out  # check_out allaqachon hisobiy

    @property
    def worked_duration(self):
        """Hisob bo'yicha ishlagan vaqt (timedelta)."""
        ci = self.billing_check_in
        co = self.billing_check_out
        if ci and co:
            delta = co - ci
            return delta if delta.total_seconds() > 0 else None
        return None

    @property
    def worked_hours_display(self) -> str:
        """'8 soat 25 daqiqa' ko'rinishida."""
        d = self.worked_duration
        if not d:
            return '—'
        total = int(d.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        if h and m:
            return f'{h} soat {m} daqiqa'
        elif h:
            return f'{h} soat'
        return f'{m} daqiqa'

    @property
    def came_early(self) -> bool:
        """Hodim smenadan oldin kelganmi."""
        if not self.check_in or not self.effective_check_in:
            return False
        return self.effective_check_in > self.check_in

    @property
    def left_late(self) -> bool:
        """Hodim smenadan keyin ketganmi (grace period hisobga olinmaydi)."""
        if not self.actual_check_out or not self.check_out:
            return False
        return self.actual_check_out > self.check_out

    # ── status sync ───────────────────────────────────────────────────────────

    def sync_status_from_schedule(self):
        """
        check_in va smena start_time asosida statusni yangilaydi.
        Faqat check_in mavjud bo'lganda ishlaydi.
        """
        if not self.check_in:
            # Absent holat — status o'zgarmaydi
            return
        shift = getattr(self.user, 'shift', None)
        if not shift or not shift.start_time:
            self.status = self.STATUS_PRESENT
            return

        from apps.attendance.views import LATE_GRACE_MINUTES  # circular import oldini olish
        local_in = timezone.localtime(self.check_in)
        diff_seconds = (
            local_in.replace(tzinfo=None) -
            local_in.replace(hour=shift.start_time.hour, minute=shift.start_time.minute, second=0, microsecond=0, tzinfo=None)
        ).total_seconds()
        diff_minutes = int(diff_seconds / 60)

        if diff_minutes > LATE_GRACE_MINUTES:
            self.status = self.STATUS_LATE
        else:
            self.status = self.STATUS_PRESENT

    def save(self, *args, **kwargs):
        # Agar update_fields berilgan bo'lsa — status sync ni o'tkazib yubormaymiz,
        # faqat check_in o'zgartirilganda
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'check_in' in update_fields:
            self.sync_status_from_schedule()
        super().save(*args, **kwargs)