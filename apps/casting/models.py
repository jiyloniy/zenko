from django.db import models
from django.conf import settings


class Stanok(models.Model):
    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Faol'
        REPAIR   = 'repair',   "Ta'mirda"
        INACTIVE = 'inactive', 'Faol emas'

    name   = models.CharField('Nomi', max_length=200)
    status = models.CharField('Holat', max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering            = ['name']
        verbose_name        = 'Stanok'
        verbose_name_plural = 'Stanoklar'

    def __str__(self):
        return self.name


class HomMahsulotLog(models.Model):
    """Stankka kiritilgan hom mahsulot yozuvi."""

    order      = models.ForeignKey(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='hom_loglar',
        verbose_name='Buyurtma',
    )
    stanok     = models.ForeignKey(
        Stanok,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='hom_loglar',
        verbose_name='Stanok',
    )
    miqdor     = models.PositiveIntegerField('Miqdor (dona)')
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Qo\'shgan',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Hom mahsulot log'
        verbose_name_plural = 'Hom mahsulot loglar'

    def __str__(self):
        return f'{self.order} → {self.stanok} | {self.miqdor} dona ({self.sana})'


class TayorMahsulotLog(models.Model):
    """Tayyor bo'lgan mahsulot yozuvi (stanoksiz)."""

    order      = models.ForeignKey(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='tayor_loglar',
        verbose_name='Buyurtma',
    )
    miqdor     = models.PositiveIntegerField('Miqdor (dona)')
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Qo\'shgan',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Tayor mahsulot log'
        verbose_name_plural = 'Tayor mahsulot loglar'

    def __str__(self):
        return f'{self.order} | {self.miqdor} dona tayyor ({self.sana})'
