from django.db import models
from django.conf import settings


class BoyashVishilka(models.Model):
    """Bo'yash bo'limi uchun vishilka — quantity par hisobida."""

    nomi     = models.CharField('Nomi', max_length=200)
    quantity = models.PositiveIntegerField(
        'Par soni (bir vishilkada)',
        default=1,
        help_text='Masalan: 25 parlik vishilka uchun 25 kiriting',
    )
    is_active  = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['quantity', 'nomi']
        verbose_name        = 'Vishilka'
        verbose_name_plural = 'Vishilkalar'

    def __str__(self):
        return f'{self.nomi} ({self.quantity} parlik)'

    @property
    def par_per_vishilka(self):
        return self.quantity


class BoyashJarayon(models.Model):
    """Har bir order uchun bo'yash jarayoni."""

    class Status(models.TextChoices):
        QABUL_QILINDI = 'qabul_qilindi', 'Qabul qilindi'
        BOYALMOQDA    = 'boyalmoqda',    "Bo'yalmoqda"
        BOYALDI       = 'boyaldi',       "Bo'yaldi"
        BOYALMADI     = 'boyalmadi',     "Bo'yalmadi"

    order = models.OneToOneField(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='boyash_jarayon',
        verbose_name='Buyurtma',
    )
    status = models.CharField(
        'Holat', max_length=20,
        choices=Status.choices, default=Status.QABUL_QILINDI,
    )
    izoh = models.TextField('Izoh / sabab', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='boyash_jarayonlar',
        verbose_name='Yaratgan',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='boyash_jarayon_updates',
        verbose_name="Oxirgi o'zgartirgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-updated_at']
        verbose_name        = "Bo'yash jarayoni"
        verbose_name_plural = "Bo'yash jarayonlari"

    def __str__(self):
        return f'{self.order} — {self.get_status_display()}'

    @property
    def status_color(self):
        return {
            self.Status.QABUL_QILINDI: 'blue',
            self.Status.BOYALMOQDA:    'orange',
            self.Status.BOYALDI:       'green',
            self.Status.BOYALMADI:     'red',
        }.get(self.status, 'gray')


class BoyashJarayonLog(models.Model):
    """Bo'yash jarayoni log — smena bo'yicha nechta vishilka bo'yaldi."""

    class Smena(models.TextChoices):
        KUN = 'kun', 'Kunduzgi smena'
        TUN = 'tun', 'Tungi smena'

    jarayon = models.ForeignKey(
        BoyashJarayon,
        on_delete=models.CASCADE,
        related_name='loglar',
        verbose_name="Bo'yash jarayoni",
    )
    smena = models.CharField(
        'Smena', max_length=5,
        choices=Smena.choices, default=Smena.KUN,
    )
    vishilka = models.ForeignKey(
        BoyashVishilka,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='loglar',
        verbose_name='Vishilka',
    )
    vishilka_soni = models.PositiveIntegerField("Bo'yalgan vishilka soni", default=1)
    izoh          = models.TextField('Izoh', blank=True)
    sana          = models.DateField('Sana')
    created_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='boyash_log_yozuvlar',
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = "Bo'yash log"
        verbose_name_plural = "Bo'yash loglar"

    def __str__(self):
        return f'{self.jarayon} | {self.get_smena_display()} ({self.sana})'

    @property
    def boyalgan_par(self):
        """Jami bo'yalgan par: vishilka.quantity × vishilka_soni."""
        if self.vishilka:
            return self.vishilka.quantity * self.vishilka_soni
        return 0
