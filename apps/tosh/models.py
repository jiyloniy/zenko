from django.db import models
from django.conf import settings


class Tosh(models.Model):
    """Tosh turlari ro'yhati — name + code."""

    name       = models.CharField('Nomi', max_length=200)
    code       = models.CharField('Kodi', max_length=50, unique=True)
    is_active  = models.BooleanField('Faol', default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tosh_yaratganlar',
        verbose_name='Yaratgan',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['name']
        verbose_name        = 'Tosh'
        verbose_name_plural = 'Toshlar'

    def __str__(self):
        return f'{self.name} [{self.code}]'


class ToshQadashJarayon(models.Model):
    """Har bir order uchun tosh qadash jarayoni."""

    class Status(models.TextChoices):
        QABUL_QILINDI  = 'qabul_qilindi',  'Qabul qilindi'
        TOSH_QADALMOQDA = 'tosh_qadalmoqda', 'Tosh qadalmoqda'
        TOSH_QADALDI   = 'tosh_qadaldi',   "Tosh qadaldi"
        TOSH_QADALMADI = 'tosh_qadalmadi', 'Tosh qadalmadi'

    order      = models.OneToOneField(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='tosh_jarayon',
        verbose_name='Buyurtma',
    )
    status     = models.CharField(
        'Holat', max_length=20,
        choices=Status.choices, default=Status.QABUL_QILINDI,
    )
    izoh       = models.TextField('Izoh / sabab', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tosh_jarayonlar',
        verbose_name='Yaratgan',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tosh_jarayon_updates',
        verbose_name="Oxirgi o'zgartirgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-updated_at']
        verbose_name        = 'Tosh qadash jarayoni'
        verbose_name_plural = 'Tosh qadash jarayonlari'

    def __str__(self):
        return f'{self.order} — {self.get_status_display()}'

    @property
    def status_color(self):
        return {
            self.Status.QABUL_QILINDI:   'blue',
            self.Status.TOSH_QADALMOQDA: 'orange',
            self.Status.TOSH_QADALDI:    'green',
            self.Status.TOSH_QADALMADI:  'red',
        }.get(self.status, 'gray') # type: ignore


class ToshQadashLog(models.Model):
    """Har bir hodim uchun log — qancha par tosh qadadi."""

    class Smena(models.TextChoices):
        KUN = 'kun', 'Kunduzgi smena'
        TUN = 'tun', 'Tungi smena'

    jarayon    = models.ForeignKey(
        ToshQadashJarayon,
        on_delete=models.CASCADE,
        related_name='loglar',
        verbose_name='Tosh qadash jarayoni',
    )
    hodim      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tosh_loglar',
        verbose_name='Hodim',
    )
    smena      = models.CharField(
        'Smena', max_length=5,
        choices=Smena.choices, default=Smena.KUN,
    )
    tosh       = models.ForeignKey(
        Tosh,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='loglar',
        verbose_name='Tosh',
    )
    par_soni   = models.PositiveIntegerField('Par soni', default=1)
    izoh       = models.TextField('Izoh', blank=True)
    sana       = models.DateField('Sana')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tosh_log_yozuvlar',
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Tosh qadash log'
        verbose_name_plural = 'Tosh qadash loglar'

    def __str__(self):
        return f'{self.jarayon} | {self.hodim} — {self.get_smena_display()} ({self.sana})'

    @property
    def qadagan_par(self):
        return self.par_soni


class KleyRasxod(models.Model):
    """Kunlik kley rasxodi — tun/kun uchun alohida, gramda. Jarayonga bog'liq emas."""

    class Smena(models.TextChoices):
        KUN = 'kun', 'Kunduzgi smena'
        TUN = 'tun', 'Tungi smena'

    smena      = models.CharField(
        'Smena', max_length=5,
        choices=Smena.choices, default=Smena.KUN,
    )
    kley_gramm = models.DecimalField(
        'Kley (gramm)', max_digits=10, decimal_places=2,
        help_text='Nechi gramm kley ketdi',
    )
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='kley_rasxodlar',
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Kley rasxodi'
        verbose_name_plural = 'Kley rasxodlari'

    def __str__(self):
        return f'{self.smena} — {self.kley_gramm}g ({self.sana})'


class ToshRasxod(models.Model):
    """Kunlik tosh rasxodi — tun/kun uchun alohida, gramda. Jarayonga bog'liq emas."""

    class Smena(models.TextChoices):
        KUN = 'kun', 'Kunduzgi smena'
        TUN = 'tun', 'Tungi smena'

    tosh       = models.ForeignKey(
        Tosh,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='rasxodlar',
        verbose_name='Tosh',
    )
    smena      = models.CharField(
        'Smena', max_length=5,
        choices=Smena.choices, default=Smena.KUN,
    )
    tosh_gramm = models.DecimalField(
        'Tosh (gramm)', max_digits=10, decimal_places=2,
        help_text='Nechi gramm tosh sarflandi',
    )
    sana       = models.DateField('Sana')
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tosh_rasxod_yozuvlar',
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Tosh rasxodi'
        verbose_name_plural = 'Tosh rasxodlari'

    def __str__(self):
        tosh_nomi = self.tosh.name if self.tosh else '—'
        return f'{tosh_nomi} | {self.get_smena_display()} — {self.tosh_gramm}g ({self.sana})'


class QabulJarayon(models.Model):
    """Qabul qilish bo'limi — tosh qadashdan keyin qabul."""

    class Status(models.TextChoices):
        KUTILMOQDA   = 'kutilmoqda',   'Kutilmoqda'
        ILINMOQDA    = 'ilinmoqda',    'Ilinmoqda'
        ILIB_BOLINDI = 'ilib_bolindi', "Ilib bo'lindi"
        BEKOR_QILINDI = 'bekor_qilindi', 'Bekor qilindi'

    tosh_jarayon = models.OneToOneField(
        ToshQadashJarayon,
        on_delete=models.CASCADE,
        related_name='qabul_jarayon',
        verbose_name='Tosh qadash jarayoni',
    )
    status     = models.CharField(
        'Holat', max_length=20,
        choices=Status.choices, default=Status.KUTILMOQDA,
    )
    izoh       = models.TextField('Izoh', blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='qabul_jarayon_updates',
        verbose_name="Oxirgi o'zgartirgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-updated_at']
        verbose_name        = 'Qabul jarayoni'
        verbose_name_plural = 'Qabul jarayonlari'

    def __str__(self):
        return f'{self.tosh_jarayon.order} — {self.get_status_display()}'

    @property
    def status_color(self):
        return {
            self.Status.KUTILMOQDA:   'gray',
            self.Status.ILINMOQDA:    'orange',
            self.Status.ILIB_BOLINDI: 'green',
            self.Status.BEKOR_QILINDI: 'red',
        }.get(self.status, 'gray')
