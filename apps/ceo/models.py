from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class SalarySettings(models.Model):
    """Har bir hodim uchun soatlik stavka."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='salary_settings',
        verbose_name='Hodim',
    )
    hourly_rate = models.DecimalField(
        'Soatlik stavka (so\'m)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Oylik sozlamalari'
        verbose_name_plural = 'Oylik sozlamalari'

    def __str__(self):
        return f'{self.user.name} — {self.hourly_rate} so\'m/soat'


class SalaryBonus(models.Model):
    """Qo'shimcha to'lov yoki KPI (oyda 1-2 marta berilishi mumkin)."""

    BONUS_TYPE_CHOICES = [
        ('bonus',    'Mukofot'),
        ('kpi',      'KPI'),
        ('penalty',  'Jarima'),
        ('other',    'Boshqa'),
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
