from django.conf import settings
from django.db import models


class Attendance(models.Model):
    """Davomat yozuvi — har bir hodimning har bir smenada kunlik davomati."""

    STATUS_CHOICES = [
        ('present', 'Keldi'),
        ('late', 'Kechikdi'),
        ('absent', 'Kelmadi'),
        ('half_day', 'Yarim kun'),
        ('early_leave', 'Erta ketdi'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Hodim',
        on_delete=models.CASCADE,
        related_name='attendances',
    )
    shift = models.ForeignKey(
        'users.Shift',
        verbose_name='Smena',
        on_delete=models.SET_NULL,
        related_name='attendances',
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        'users.Branch',
        verbose_name='Filial',
        on_delete=models.CASCADE,
        related_name='attendances',
    )
    date = models.DateField('Sana')
    check_in = models.DateTimeField('Kirish vaqti', null=True, blank=True)
    check_out = models.DateTimeField('Chiqish vaqti', null=True, blank=True)
    is_overtime = models.BooleanField('Qo\'shimcha smena', default=False)
    photo = models.ImageField(
        'Rasm',
        upload_to='attendance_photos/%Y/%m/%d/',
        null=True,
        blank=True,
    )
    status = models.CharField(
        'Holat',
        max_length=20,
        choices=STATUS_CHOICES,
        default='present',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Davomat'
        verbose_name_plural = 'Davomatlar'
        ordering = ['-date', '-check_in']

    def __str__(self):
        overtime = ' (Qo\'shimcha)' if self.is_overtime else ''
        return f'{self.user.name} — {self.date} ({self.get_status_display()}){overtime}'

    @property
    def worked_duration(self):
        """Ishlagan vaqt hisoblash."""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            return delta
        return None

    @property
    def worked_hours_display(self):
        """Ishlangan soatlarni chiroyli ko'rsatish."""
        d = self.worked_duration
        if d:
            total_seconds = int(d.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f'{hours} soat {minutes} daqiqa'
        return '—'
