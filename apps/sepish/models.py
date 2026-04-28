from django.db import models
from django.conf import settings


class Kraska(models.Model):
    """Sepish uchun kraska — code va name."""

    code      = models.CharField('Kodi', max_length=50, unique=True)
    name      = models.CharField('Nomi', max_length=200)
    color_hex = models.CharField('Rang (hex)', max_length=7, default='#6B7280',
                                 help_text='Masalan: #FF5500')
    is_active = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['code']
        verbose_name        = 'Kraska'
        verbose_name_plural = 'Kraskalar'

    def __str__(self):
        return f'{self.code} — {self.name}'


class SepishJarayon(models.Model):
    """Har bir order uchun sepish jarayoni."""

    class Status(models.TextChoices):
        QABUL_QILINDI = 'qabul_qilindi', 'Qabul qilindi'
        SEPILMOQDA    = 'sepilmoqda',    'Sepilmoqda'
        SEPILDI       = 'sepildi',       'Sepildi'
        SEPILMADI     = 'sepilmadi',     'Sepilmadi'

    order = models.OneToOneField(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='sepish_jarayon',
        verbose_name='Buyurtma',
    )
    status = models.CharField(
        'Holat', max_length=20,
        choices=Status.choices, default=Status.QABUL_QILINDI,
    )
    izoh = models.TextField('Izoh / sabab', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sepish_jarayonlar',
        verbose_name='Yaratgan',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sepish_jarayon_updates',
        verbose_name="Oxirgi o'zgartirgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-updated_at']
        verbose_name        = 'Sepish jarayoni'
        verbose_name_plural = 'Sepish jarayonlari'

    def __str__(self):
        return f'{self.order} — {self.get_status_display()}'

    @property
    def status_color(self):
        return {
            self.Status.QABUL_QILINDI: 'blue',
            self.Status.SEPILMOQDA:    'violet',
            self.Status.SEPILDI:       'green',
            self.Status.SEPILMADI:     'red',
        }.get(self.status, 'gray')


class SepishJarayonLog(models.Model):
    """Sepish log — smena bo'yicha nechta par, qancha gram kraska."""

    class Smena(models.TextChoices):
        KUN = 'kun', 'Kunduzgi smena'
        TUN = 'tun', 'Tungi smena'

    jarayon = models.ForeignKey(
        SepishJarayon,
        on_delete=models.CASCADE,
        related_name='loglar',
        verbose_name='Sepish jarayoni',
    )
    smena = models.CharField(
        'Smena', max_length=5,
        choices=Smena.choices, default=Smena.KUN,
    )
    par_soni = models.PositiveIntegerField(
        'Sepilgan par soni', default=1,
        help_text='Nechta par sepildi',
    )
    kraska = models.ForeignKey(
        Kraska,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='loglar',
        verbose_name='Kraska',
    )
    kraska_gramm = models.PositiveIntegerField(
        'Kraska (gramm)', default=0,
        help_text='Necha gramm kraska ketdi',
    )
    izoh = models.TextField('Izoh', blank=True)
    sana = models.DateField('Sana')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sepish_log_yozuvlar',
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sepish_log_updates',
        verbose_name="Tahrirlagan",
    )

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Sepish log'
        verbose_name_plural = 'Sepish loglar'

    def __str__(self):
        return f'{self.jarayon} | {self.get_smena_display()} ({self.sana})'
