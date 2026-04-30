from django.db import models
from django.conf import settings



class Vishilka(models.Model):
    """Ilish bo'limi uchun vishilka — quantity par hisobida."""

    nomi       = models.CharField('Nomi', max_length=200)
    quantity   = models.PositiveIntegerField(
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
    def broshka_per_vishilka(self):
        """Bir vishilkadagi broshka soni = par × 2 (o'ng + chap)."""
        return self.quantity * 2


class IlishJarayon(models.Model):
    """Har bir order uchun ilish jarayoni."""

    class Status(models.TextChoices):
        QABUL_QILINDI = 'qabul_qilindi', 'Qabul qilindi'
        ILINMOQDA     = 'ilinmoqda',     'Ilinmoqda'
        ILIB_BOLINDI  = 'ilib_bolindi',  "Ilib bo'lindi"
        BEKOR_QILINDI = 'bekor_qilindi', 'Bekor qilindi'

    order      = models.OneToOneField(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='ilish_jarayon',
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
        related_name='ilish_jarayonlar',
        verbose_name='Yaratgan',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ilish_jarayon_updates',
        verbose_name="Oxirgi o'zgartirgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-updated_at']
        verbose_name        = 'Ilish jarayoni'
        verbose_name_plural = 'Ilish jarayonlari'

    def __str__(self):
        return f'{self.order} — {self.get_status_display()}'

    @property
    def status_color(self):
        return {
            self.Status.QABUL_QILINDI: 'blue',
            self.Status.ILINMOQDA:     'orange',
            self.Status.ILIB_BOLINDI:  'green',
            self.Status.BEKOR_QILINDI: 'red',
        }.get(self.status, 'gray')


class IlishJarayonLog(models.Model):
    """Ilish jarayoni log yozuvi — hodim smena bo'yicha kiritadi."""

    class Smena(models.TextChoices):
        KUN = 'kun', 'Kunduzgi smena'
        TUN = 'tun', 'Tungi smena'

    jarayon       = models.ForeignKey(
        IlishJarayon,
        on_delete=models.CASCADE,
        related_name='loglar',
        verbose_name='Ilish jarayoni',
    )
    hodim         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ilish_loglar',
        verbose_name='Hodim',
    )
    smena         = models.CharField(
        'Smena', max_length=5,
        choices=Smena.choices, default=Smena.KUN,
    )
    vishilka      = models.ForeignKey(
        Vishilka,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='loglar',
        verbose_name='Vishilka',
    )
    vishilka_soni = models.PositiveIntegerField('Vishilka soni', default=1)
    izoh          = models.TextField('Izoh', blank=True)
    sana          = models.DateField('Sana')
    created_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ilish_log_yozuvlar',
        verbose_name="Qo'shgan",
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Ilish log'
        verbose_name_plural = 'Ilish loglar'

    def __str__(self):
        return f'{self.jarayon} | {self.hodim} — {self.get_smena_display()} ({self.sana})'

    @property
    def ilingan_par(self):
        """Ilingan par soni: vishilka.quantity × vishilka_soni."""
        if self.vishilka:
            return self.vishilka.quantity * self.vishilka_soni
        return 0

    @property
    def ilingan_broshka(self):
        """Ilingan broshka soni: par × 2 (o'ng + chap tomon)."""
        return self.ilingan_par * 2


# ─────────────────────────────────────────────
# Upakovka (Qadoqlash) — ilish tugagach
# ─────────────────────────────────────────────

class QadoqlashJarayon(models.Model):
    """Upakovka jarayoni — ilib_bolindi statusli IlishJarayon dan avtomatik yaratiladi."""

    class Status(models.TextChoices):
        QABUL_QILINDI = 'qabul_qilindi', 'Qabul qilindi'
        QADOQLANMOQDA = 'qadoqlanmoqda', 'Qadoqlanmoqda'
        QADOQLANDI    = 'qadoqlandi',    'Qadoqlandi'
        QADOQLANMADI  = 'qadoqlanmadi',  'Qadoqlanmadi'

    ilish_jarayon = models.OneToOneField(
        IlishJarayon,
        on_delete=models.CASCADE,
        related_name='qadoqlash_jarayon',
        verbose_name='Ilish jarayoni',
    )
    status     = models.CharField(
        'Holat', max_length=20,
        choices=Status.choices, default=Status.QABUL_QILINDI,
    )
    izoh       = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='qadoqlash_jarayonlar',
        verbose_name='Yaratgan',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='qadoqlash_jarayon_updates',
        verbose_name="Oxirgi o'zgartirgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-updated_at']
        verbose_name        = 'Qadoqlash jarayoni'
        verbose_name_plural = 'Qadoqlash jarayonlari'

    def __str__(self):
        return f'{self.ilish_jarayon.order} — {self.get_status_display()}'

    @property
    def order(self):
        return self.ilish_jarayon.order

    @property
    def status_color(self):
        return {
            self.Status.QABUL_QILINDI: 'blue',
            self.Status.QADOQLANMOQDA: 'orange',
            self.Status.QADOQLANDI:    'green',
            self.Status.QADOQLANMADI:  'red',
        }.get(self.status, 'gray')  # type: ignore


class QadoqlashLog(models.Model):
    """Upakovka log — nechi par qadoqlandi (kun/tun smena)."""

    class Smena(models.TextChoices):
        KUN = 'kun', 'Kunduzgi smena'
        TUN = 'tun', 'Tungi smena'

    smena      = models.CharField(
        'Smena', max_length=5,
        choices=Smena.choices, default=Smena.KUN,
    )
    par_soni   = models.PositiveIntegerField('Par soni', default=1)
    izoh       = models.TextField('Izoh', blank=True)
    sana       = models.DateField('Sana')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='qadoqlash_log_yozuvlar',
        verbose_name="Qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-sana', '-created_at']
        verbose_name        = 'Qadoqlash log'
        verbose_name_plural = 'Qadoqlash loglar'

    def __str__(self):
        return f'{self.get_smena_display()} — {self.par_soni} par ({self.sana})'
