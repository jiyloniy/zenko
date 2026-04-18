from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.users.models import Branch


class Attendance(models.Model):
    """
    Davomat: kirish/chiqish vaqtlari + filial.
    Kechikish: hodimning smenasi (user.shift) boshlanish vaqti bilan solishtiriladi.
    """

    STATUS_PRESENT = 'present'
    STATUS_LATE = 'late'
    STATUS_ABSENT = 'absent'

    STATUS_CHOICES = (
        (STATUS_PRESENT, 'Vaqtida keldi'),
        (STATUS_LATE, 'Kechikdi'),
        (STATUS_ABSENT, 'Kelmadi'),
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
    date = models.DateField('Sana')
    check_in = models.DateTimeField('Kirish vaqti', null=True, blank=True)
    check_out = models.DateTimeField('Chiqish vaqti', null=True, blank=True)
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
        verbose_name = 'Davomat'
        verbose_name_plural = 'Davomatlar'
        ordering = ['-date', '-check_in']

    def __str__(self):
        return f'{self.user} — {self.date}'

    @property
    def worked_duration(self):
        if self.check_in and self.check_out:
            return self.check_out - self.check_in
        return None

    @property
    def worked_hours_display(self):
        d = self.worked_duration
        if d:
            total_seconds = int(d.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f'{hours} soat {minutes} daqiqa'
        return '—'

    def sync_status_from_schedule(self):
        """Kirish vaqti va hodim smenasi bo'yicha statusni yangilash (kiosk / tahrirlash)."""
        if self.status == self.STATUS_ABSENT and not self.check_in:
            return
        if not self.check_in:
            return
        shift = getattr(self.user, 'shift', None)
        if not shift or not shift.start_time:
            self.status = self.STATUS_PRESENT
            return
        local_in = timezone.localtime(self.check_in)
        if local_in.time() > shift.start_time:
            self.status = self.STATUS_LATE
        else:
            self.status = self.STATUS_PRESENT

    def save(self, *args, **kwargs):
        self.sync_status_from_schedule()
        super().save(*args, **kwargs)
