from decimal import Decimal

from django.conf import settings
from django.db import models


class HourlyRateHistory(models.Model):
    """
    Hodimning soatlik stavka tarixi.
    Har yangi stavka qo'shilganda effective_from sanasidan boshlab amal qiladi.
    Eski yozuvlar o'sha vaqtdagi stavka bilan hisoblanadi.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rate_history',
        verbose_name='Hodim',
    )
    hourly_rate = models.DecimalField(
        'Soatlik stavka (so\'m)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    effective_from = models.DateField(
        'Amal qilish boshlanishi',
        help_text='Shu sanadan boshlab ushbu stavka hisoblanadi.',
    )
    note = models.CharField('Izoh', max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stavka tarixi'
        verbose_name_plural = 'Stavka tarixi'
        ordering = ['-effective_from']
        unique_together = [['user', 'effective_from']]

    def __str__(self):
        return f'{self.user.name}: {self.hourly_rate} so\'m/soat ({self.effective_from})'

    @classmethod
    def rate_for_date(cls, user, date):
        """O'sha sana uchun to'g'ri stavkani qaytaradi."""
        entry = (
            cls.objects.filter(user=user, effective_from__lte=date)
            .order_by('-effective_from')
            .first()
        )
        if entry:
            return entry.hourly_rate
        # Hech qanday tariх yo'q — 0
        return Decimal('0.00')

    @classmethod
    def current_rate(cls, user):
        """Hozirgi (eng so'nggi) stavka."""
        entry = cls.objects.filter(user=user).order_by('-effective_from').first()
        return entry.hourly_rate if entry else Decimal('0.00')


class SalaryBonus(models.Model):
    """Qo'shimcha to'lov yoki KPI / jarima (oyda 1-2 marta berilishi mumkin)."""

    BONUS_TYPE_CHOICES = [
        ('bonus',   'Mukofot'),
        ('kpi',     'KPI'),
        ('penalty', 'Jarima'),
        ('other',   'Boshqa'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='salary_bonuses',
        verbose_name='Hodim',
    )
    year  = models.PositiveSmallIntegerField('Yil')
    month = models.PositiveSmallIntegerField('Oy')
    bonus_type = models.CharField(
        'Turi', max_length=20, choices=BONUS_TYPE_CHOICES, default='bonus',
    )
    amount = models.DecimalField(
        'Miqdor (so\'m)', max_digits=14, decimal_places=2,
    )
    note = models.CharField('Izoh', max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bonus/KPI'
        verbose_name_plural = 'Bonus/KPI'
        ordering = ['-year', '-month', '-created_at']

    def __str__(self):
        sign = '-' if self.bonus_type == 'penalty' else '+'
        return f'{self.user.name} {self.year}/{self.month:02d} {sign}{self.amount}'

    @property
    def is_deduction(self):
        return self.bonus_type == 'penalty'
