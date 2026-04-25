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


class Zamak(models.Model):
    """Zamak turlari — rasxod uchun material."""
    name       = models.CharField('Nomi', max_length=200)
    unit       = models.CharField('O\'lchov birligi', max_length=30, default='kg',
                                  help_text='kg, litr, dona va h.k.')
    is_active  = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['name']
        verbose_name        = 'Zamak'
        verbose_name_plural = 'Zamaklar'

    def __str__(self):
        return f'{self.name} ({self.unit})'


class RasxodLog(models.Model):
    """Stanokda ishlatiladigan zamak rasxodi."""
    stanok     = models.ForeignKey(
        Stanok,
        on_delete=models.CASCADE,
        related_name='rasxodlar',
        verbose_name='Stanok',
    )
    zamak      = models.ForeignKey(
        Zamak,
        on_delete=models.PROTECT,
        related_name='rasxodlar',
        verbose_name='Zamak',
    )
    miqdor     = models.DecimalField('Miqdor', max_digits=10, decimal_places=2)
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Rasxod'
        verbose_name_plural = 'Rasxodlar'

    def __str__(self):
        return f'{self.stanok} | {self.zamak} — {self.miqdor} ({self.sana})'


class AdditionalOrder(models.Model):
    """Sinov/qo'shimcha buyurtma — broshkasiz, qolip sinovi uchun."""

    class Status(models.TextChoices):
        NEW        = 'new',        'Yangi'
        IN_PROCESS = 'in_process', 'Ishlab chiqarilmoqda'
        DONE       = 'done',       'Tugallandi'
        CANCELLED  = 'cancelled',  'Bekor qilindi'

    order_number = models.CharField('Raqam', max_length=20, unique=True, blank=True)
    name         = models.CharField('Nomi', max_length=255)
    quantity     = models.PositiveIntegerField('Miqdor')
    deadline     = models.DateField('Muddat')
    status       = models.CharField('Holat', max_length=20,
                                    choices=Status.choices, default=Status.NEW)
    note         = models.TextField('Izoh', blank=True)
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Yaratgan',
        related_name='additional_orders',
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Qo\'shimcha buyurtma'
        verbose_name_plural = 'Qo\'shimcha buyurtmalar'

    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.utils.crypto import get_random_string
            self.order_number = f'#ADD{get_random_string(6, "0123456789")}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.order_number} — {self.name}'

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.deadline < timezone.now().date()
            and self.status not in (self.Status.DONE, self.Status.CANCELLED)
        )


class AdditionalHomLog(models.Model):
    """Qo'shimcha buyurtma uchun hom mahsulot logi."""
    add_order  = models.ForeignKey(
        AdditionalOrder,
        on_delete=models.CASCADE,
        related_name='hom_loglar',
        verbose_name='Qo\'shimcha buyurtma',
    )
    stanok     = models.ForeignKey(
        Stanok,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='add_hom_loglar',
        verbose_name='Stanok',
    )
    miqdor     = models.PositiveIntegerField('Miqdor (dona)')
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Qo\'shimcha hom log'
        verbose_name_plural = 'Qo\'shimcha hom loglar'

    def __str__(self):
        return f'{self.add_order} | {self.miqdor} dona ({self.sana})'


class AdditionalTayorLog(models.Model):
    """Qo'shimcha buyurtma uchun tayor mahsulot logi."""
    add_order  = models.ForeignKey(
        AdditionalOrder,
        on_delete=models.CASCADE,
        related_name='tayor_loglar',
        verbose_name='Qo\'shimcha buyurtma',
    )
    miqdor     = models.PositiveIntegerField('Miqdor (dona)')
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Qo\'shimcha tayor log'
        verbose_name_plural = 'Qo\'shimcha tayor loglar'

    def __str__(self):
        return f'{self.add_order} | {self.miqdor} dona tayyor ({self.sana})'


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
        verbose_name="Qo'shgan",
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
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Tayor mahsulot log'
        verbose_name_plural = 'Tayor mahsulot loglar'

    def __str__(self):
        return f'{self.order} | {self.miqdor} dona tayyor ({self.sana})'


class QuyishRasxod(models.Model):
    """Quyish bo'limi uchun mustaqil rasxod yozuvi."""

    nomi       = models.CharField('Nomi', max_length=300)
    miqdor     = models.DecimalField('Miqdor', max_digits=10, decimal_places=2)
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Quyish rasxodi'
        verbose_name_plural = 'Quyish rasxodlari'

    def __str__(self):
        return f'{self.nomi} — {self.miqdor} ({self.sana})'
