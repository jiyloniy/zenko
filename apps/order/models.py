from django.db import models
from django.conf import settings


# ──────────────────────────────────────────────
#  STANOK
# ──────────────────────────────────────────────
class Stanok(models.Model):
    name   = models.CharField('Stanok nomi', max_length=100, unique=True)
    model  = models.CharField('Model', max_length=100, blank=True)
    is_active = models.BooleanField('Faol', default=True)
    note   = models.TextField('Izoh', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Stanok'
        verbose_name_plural = 'Stanoklar'

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────
#  STANOK LOGI (yarim tayyor mahsulot hisobi)
# ──────────────────────────────────────────────
class StanokLog(models.Model):
    """Stanokdan chiqqan yarim tayyor mahsulot logi. OrderStageLog dan alohida."""

    class Side(models.TextChoices):
        TOP    = 'top',    'Yuqori tomon'
        BOTTOM = 'bottom', 'Pastki tomon'
        SINGLE = 'single', 'Bir tomonlama'

    order    = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='stanok_logs', verbose_name='Buyurtma')
    stanok   = models.ForeignKey(Stanok, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs', verbose_name='Stanok')
    worker   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='stanok_logs', verbose_name='Ishchi')
    quantity = models.PositiveIntegerField('Miqdori')
    defect   = models.PositiveIntegerField('Yaroqsiz', default=0)
    side     = models.CharField('Tomoni', max_length=10, choices=Side.choices, default=Side.SINGLE)
    note     = models.TextField('Izoh', blank=True)
    created_at = models.DateTimeField('Vaqt', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stanok logi'
        verbose_name_plural = 'Stanok loglari'

    def __str__(self):
        return f"{self.order.order_number} | {self.stanok} | {self.quantity} dona ({self.get_side_display()})"


# ──────────────────────────────────────────────
#  BO'LIMDAN BO'LIMGA O'TKAZISH (TRANSFER)
# ──────────────────────────────────────────────
class StageTransfer(models.Model):
    """
    Bir bo'limdan ikkinchisiga mahsulot o'tkazish.
    Yuboruvchi transfer yaratadi, qabul qiluvchi accept qiladi.
    """

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Kutilmoqda'
        ACCEPTED = 'accepted', 'Qabul qilindi'
        REJECTED = 'rejected', 'Rad etildi'

    class Stage(models.TextChoices):
        CASTING       = 'casting',       "Quyish bo'limi"
        ATTACH        = 'attach',        "Ilish bo'limi"
        SPRAY         = 'spray',         "Sepish bo'limi"
        PAINT         = 'paint',         "Bo'yash bo'limi"
        PACKAGING     = 'packaging',     "Upakovka bo'limi"
        STONE         = 'stone',         "Tosh qadash bo'limi"
        MONTAJ        = 'montaj',        "Montaj bo'limi"
        HANGING       = 'hanging',       "Ilish bo'limi (eski)"
        STONE_SETTING = 'stone_setting', "Tosh qadash bo'limi (eski)"
        WAREHOUSE     = 'warehouse',     "Ombor"

    order         = models.ForeignKey(
        'Order', on_delete=models.CASCADE,
        related_name='transfers', verbose_name='Buyurtma',
    )
    from_stage    = models.CharField('Qaysi bo\'limdan', max_length=20, choices=Stage.choices)
    to_stage      = models.CharField('Qaysi bo\'limga',  max_length=20, choices=Stage.choices)
    status        = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    sent_quantity     = models.PositiveIntegerField('Yuborilgan miqdor')
    accepted_quantity = models.PositiveIntegerField('Qabul qilingan miqdor', default=0)
    rejected_quantity = models.PositiveIntegerField('Rad etilgan miqdor', default=0)

    sent_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transfers_sent',
        verbose_name='Yuboruvchi',
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transfers_accepted',
        verbose_name='Qabul qiluvchi',
    )

    note          = models.TextField('Izoh (yuboruvchi)', blank=True)
    accept_note   = models.TextField('Izoh (qabul qiluvchi)', blank=True)

    sent_at       = models.DateTimeField('Yuborilgan vaqt', auto_now_add=True)
    accepted_at   = models.DateTimeField('Qabul qilingan vaqt', null=True, blank=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = "Bo'limlar arasi transfer"
        verbose_name_plural = "Bo'limlar arasi transferlar"

    def __str__(self):
        return (
            f"{self.order.order_number}: "
            f"{self.get_from_stage_display()} → {self.get_to_stage_display()} "
            f"({self.sent_quantity} dona) [{self.get_status_display()}]"
        )


# ──────────────────────────────────────────────
#  ASOSIY BUYURTMA
# ──────────────────────────────────────────────
class Order(models.Model):

    class Status(models.TextChoices):
        NEW        = 'new',        'Yangi'
        ACCEPTED   = 'accepted',   'Qabul qilindi'
        IN_PROCESS = 'in_process', 'Ishlab chiqarilmoqda'
        READY      = 'ready',      'Tayyor'
        DELIVERED  = 'delivered',   'Topshirildi'
        CANCELLED  = 'cancelled',  'Bekor qilindi'

    class CurrentStage(models.TextChoices):
        CASTING       = 'casting',       'Quyish bo\'limi'
        ATTACH        = 'attach',        'Ilish bo\'limi'
        SPRAY         = 'spray',         'Sepish bo\'limi'
        PAINT         = 'paint',         'Bo\'yash bo\'limi'
        PACKAGING     = 'packaging',     'Upakovka bo\'limi'
        STONE         = 'stone',         'Tosh qadash bo\'limi'
        MONTAJ        = 'montaj',        'Montaj bo\'limi'
        HANGING       = 'hanging',       'Ilish bo\'limi (eski)'
        STONE_SETTING = 'stone_setting', 'Tosh qadash bo\'limi (eski)'
        WAREHOUSE     = 'warehouse',     'Ombor'
        OUTSOURCE     = 'outsource',     'Tashqi ishlov'

    class CoatingType(models.TextChoices):
        SPRAY_ONLY      = 'spray_only',      'Faqat sepish'
        PAINT_ONLY      = 'paint_only',      'Faqat bo\'yash'
        SPRAY_AND_PAINT = 'spray_and_paint', 'Sepish va bo\'yash'

    class Priority(models.TextChoices):
        LOW    = 'low',    'Past'
        NORMAL = 'normal', 'Oddiy'
        HIGH   = 'high',   'Yuqori'
        URGENT = 'urgent', 'Shoshilinch'

    order_number = models.CharField('Buyurtma raqami', max_length=20, unique=True, blank=True)
    name     = models.CharField('Buyurtma nomi', max_length=255)
    def save(self, *args, **kwargs):
            if not self.order_number:
                from django.utils.crypto import get_random_string
                self.order_number = f"ORD{get_random_string(6, '0123456789') }"
            super().save(*args, **kwargs)
    quantity = models.PositiveIntegerField('Miqdori')
    image    = models.ImageField(
        'Rasm',
        upload_to='orders/%Y/%m/',
        blank=True,
        null=True,
    )
    deadline      = models.DateField('Tayyor bo\'lish sanasi')
    status        = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.NEW)
    current_stage = models.CharField('Joriy bo\'lim', max_length=20, choices=CurrentStage.choices, blank=True)
    coating_type  = models.CharField(
        'Qoplama turi', max_length=20, choices=CoatingType.choices,
        default=CoatingType.SPRAY_ONLY,
    )
    has_stone     = models.BooleanField('Tosh qadash bormi', default=False)
    has_assembly  = models.BooleanField('Montaj bormi', default=False)
    priority      = models.CharField(
        'Muhimlik darajasi', max_length=10, choices=Priority.choices,
        default=Priority.NORMAL,
    )
    note          = models.TextField('Izoh', blank=True)
    created_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Yaratuvchi',
        related_name='created_orders',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField('Yaratilgan vaqt', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan vaqt', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Buyurtma'
        verbose_name_plural = 'Buyurtmalar'

    def __str__(self):
        return f'{self.name} — {self.quantity} dona'

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.deadline < timezone.now().date()
            and self.status not in (self.Status.DELIVERED, self.Status.CANCELLED)
        )

    @property
    def total_defect(self):
        total = 0
        for rel in ('casting', 'montaj', 'hanging', 'stone_setting', 'packaging'):
            stage = getattr(self, rel, None)
            if stage:
                total += stage.defect_quantity
        return total

    @property
    def good_quantity(self):
        return self.quantity - self.total_defect


# ──────────────────────────────────────────────
#  1. QUYISH BO'LIMI
# ──────────────────────────────────────────────
class CastingStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Quyilmoqda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='casting',
    )
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    total_quantity     = models.PositiveIntegerField('Umumiy miqdor', default=0)
    defect_quantity    = models.PositiveIntegerField('Yaroqsiz', default=0)
        # Endi worker emas, harakatlar logi orqali ko'p ishchi bo'ladi
        # ...existing code...

    # ──────────────────────────────────────────────
    #  BOSQICH HARAKATLARI TARIXI (LOG)
    # ──────────────────────────────────────────────
    note= models.TextField('Izoh', blank=True)
    started_at = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Quyish bosqichi'
        verbose_name_plural = 'Quyish bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Quyish ({self.get_status_display()})'
    
class OrderStageLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='stage_logs')
    stage = models.CharField('Bosqich', max_length=20, choices=Order.CurrentStage.choices)
    from_department = models.CharField('Qaysi bo\'limdan', max_length=50, blank=True)
    to_department = models.CharField('Qaysi bo\'limga', max_length=50)
    quantity = models.PositiveIntegerField('Miqdori')
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_stage_logs')
    stanok = models.ForeignKey('Stanok', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_stage_logs', verbose_name='Stanok')
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='stage_accepted_logs')
    note = models.TextField('Izoh', blank=True)
    created_at = models.DateTimeField('Vaqt', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bosqich harakati'
        verbose_name_plural = 'Bosqich harakatlari'

    def __str__(self):
        return f"{self.order.order_number} - {self.get_stage_display()} ({self.quantity} dona) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# ──────────────────────────────────────────────
#  ILISH BO'LIMI (yangi: attach)
# ──────────────────────────────────────────────
class AttachStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Ilinmoqda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='attach', verbose_name='Buyurtma')
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)
    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)
    note       = models.TextField('Izoh', blank=True)
    started_at  = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Ilish bosqichi'
        verbose_name_plural = 'Ilish bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Ilish ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  SEPISH BO'LIMI (spray)
# ──────────────────────────────────────────────
class SprayStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Sepilyapti'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    class LayerType(models.TextChoices):
        SPRAY = 'spray', 'Sepish'
        PAINT = 'paint', "Bo'yash"

    order        = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='spray', verbose_name='Buyurtma')
    status       = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)
    layer_number = models.PositiveSmallIntegerField('Qavat raqami', default=1)
    layer_type   = models.CharField('Qavat turi', max_length=10, choices=LayerType.choices, default=LayerType.SPRAY)
    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)
    note       = models.TextField('Izoh', blank=True)
    started_at  = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Sepish bosqichi'
        verbose_name_plural = 'Sepish bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Sepish ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  BO'YASH BO'LIMI (paint)
# ──────────────────────────────────────────────
class PaintStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', "Bo'yalmoqda"
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order        = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='paint', verbose_name='Buyurtma')
    status       = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)
    layer_number = models.PositiveSmallIntegerField('Qavat raqami', default=2)
    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)
    note       = models.TextField('Izoh', blank=True)
    started_at  = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = "Bo'yash bosqichi"
        verbose_name_plural = "Bo'yash bosqichlari"

    def __str__(self):
        return f"{self.order.name} — Bo'yash ({self.get_status_display()})"


# ──────────────────────────────────────────────
#  TOSH QADASH BO'LIMI (yangi: stone)
# ──────────────────────────────────────────────
class StoneStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Tosh qadashda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='stone', verbose_name='Buyurtma')
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)
    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)
    note       = models.TextField('Izoh', blank=True)
    started_at  = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Tosh qadash bosqichi'
        verbose_name_plural = 'Tosh qadash bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Tosh qadash ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  MONTAJ BO'LIMI (yangi)
# ──────────────────────────────────────────────
class AssemblyStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Montajda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='assembly', verbose_name='Buyurtma')
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)
    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)
    note       = models.TextField('Izoh', blank=True)
    started_at  = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Montaj bosqichi'
        verbose_name_plural = 'Montaj bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Montaj ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  UPAKOVKA BO'LIMI (yangi)
# ──────────────────────────────────────────────
class PackStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Qadoqlanmoqda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='pack', verbose_name='Buyurtma')
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)
    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    packed_quantity = models.PositiveIntegerField('Qadoqlangan', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)
    note       = models.TextField('Izoh', blank=True)
    started_at  = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Upakovka bosqichi'
        verbose_name_plural = 'Upakovka bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Upakovka ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  2. MONTAJ BO'LIMI  (til qadash)
# ──────────────────────────────────────────────
class MontajStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Til qadashda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='montaj',
    )
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    total_quantity     = models.PositiveIntegerField('Umumiy miqdor', default=0)
    assembled_quantity = models.PositiveIntegerField('Til qadalgan', default=0)
    defect_quantity    = models.PositiveIntegerField('Yaroqsiz', default=0)

    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Ishchi',
        related_name='montaj_works',
        blank=True,
        null=True,
    )
    note       = models.TextField('Izoh', blank=True)
    started_at = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Montaj bosqichi'
        verbose_name_plural = 'Montaj bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Montaj ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  3. ILISH BO'LIMI  (vishilkaga ilish + himiya)
# ──────────────────────────────────────────────
class HangingStage(models.Model):

    class Status(models.TextChoices):
        PENDING       = 'pending',       'Kutilmoqda'
        HANGING       = 'hanging',       'Vishilkaga ilishda'
        CHEMICAL_SOAK = 'chemical_soak', 'Himiyada bo\'ktirishda'
        COMPLETED     = 'completed',     'Yakunlandi'
        REJECTED      = 'rejected',      'Rad etildi'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='hanging',
    )
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    hung_quantity   = models.PositiveIntegerField('Ilingan', default=0)
    soaked_quantity = models.PositiveIntegerField('Bo\'ktirilgan', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)

    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Ishchi',
        related_name='hanging_works',
        blank=True,
        null=True,
    )
    note       = models.TextField('Izoh', blank=True)
    started_at = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Ilish bosqichi'
        verbose_name_plural = 'Ilish bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Ilish ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  4. TOSH QADASH BO'LIMI
# ──────────────────────────────────────────────
class StoneSettingStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Tosh qadashda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='stone_setting',
    )
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    total_quantity      = models.PositiveIntegerField('Umumiy miqdor', default=0)
    stones_set_quantity = models.PositiveIntegerField('Tosh qadalgan', default=0)
    defect_quantity     = models.PositiveIntegerField('Yaroqsiz', default=0)

    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Ishchi',
        related_name='stone_setting_works',
        blank=True,
        null=True,
    )
    note       = models.TextField('Izoh', blank=True)
    started_at = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Tosh qadash bosqichi'
        verbose_name_plural = 'Tosh qadash bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Tosh qadash ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  5. UPAKOVKA BO'LIMI
# ──────────────────────────────────────────────
class PackagingStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        IN_PROCESS = 'in_process', 'Qadoqlanmoqda'
        COMPLETED  = 'completed',  'Yakunlandi'
        REJECTED   = 'rejected',   'Rad etildi'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='packaging',
    )
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    total_quantity  = models.PositiveIntegerField('Umumiy miqdor', default=0)
    packed_quantity = models.PositiveIntegerField('Qadoqlangan', default=0)
    defect_quantity = models.PositiveIntegerField('Yaroqsiz', default=0)

    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Ishchi',
        related_name='packaging_works',
        blank=True,
        null=True,
    )
    note       = models.TextField('Izoh', blank=True)
    started_at = models.DateTimeField('Boshlangan vaqt', blank=True, null=True)
    finished_at = models.DateTimeField('Tugallangan vaqt', blank=True, null=True)
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Upakovka bosqichi'
        verbose_name_plural = 'Upakovka bosqichlari'

    def __str__(self):
        return f'{self.order.name} — Upakovka ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  6. OMBOR
# ──────────────────────────────────────────────
class WarehouseStage(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Kutilmoqda'
        RECEIVED   = 'received',   'Qabul qilindi'
        DELIVERING = 'delivering', 'Yetkazilmoqda'
        DELIVERED  = 'delivered',  'Haridorga topshirildi'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='warehouse',
    )
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    received_quantity  = models.PositiveIntegerField('Qabul qilingan', default=0)
    delivered_quantity = models.PositiveIntegerField('Yetkazilgan', default=0)

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Qabul qiluvchi',
        related_name='warehouse_receives',
        blank=True,
        null=True,
    )
    note        = models.TextField('Izoh', blank=True)
    received_at = models.DateTimeField('Qabul qilingan vaqt', blank=True, null=True)
    delivered_at = models.DateTimeField('Yetkazilgan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Ombor'
        verbose_name_plural = 'Ombor'

    def __str__(self):
        return f'{self.order.name} — Ombor ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  7. TASHQI ISHLOV  (tashqarida qildiriladigan ishlar)
# ──────────────────────────────────────────────
class OutsourceWork(models.Model):

    class Status(models.TextChoices):
        PENDING     = 'pending',     'Kutilmoqda'
        SENT        = 'sent',        'Yuborildi'
        IN_PROCESS  = 'in_process',  'Bajarilmoqda'
        RECEIVED    = 'received',    'Qaytib keldi'
        COMPLETED   = 'completed',   'Yakunlandi'
        REJECTED    = 'rejected',    'Rad etildi'

    class ReturnStage(models.TextChoices):
        CASTING       = 'casting',       'Quyish bo\'limiga'
        MONTAJ        = 'montaj',        'Montaj bo\'limiga'
        HANGING       = 'hanging',       'Ilish bo\'limiga'
        STONE_SETTING = 'stone_setting', 'Tosh qadash bo\'limiga'
        PACKAGING     = 'packaging',     'Upakovka bo\'limiga'

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='outsource_works',
    )
    status = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.PENDING)

    work_description = models.TextField('Bajariladigan ish tavsifi')
    contractor       = models.CharField('Pudratchi (tashqi ustaxona)', max_length=255)
    contractor_phone = models.CharField('Pudratchi telefoni', max_length=20, blank=True)

    sent_quantity     = models.PositiveIntegerField('Yuborilgan miqdor', default=0)
    received_quantity = models.PositiveIntegerField('Qaytib kelgan', default=0)
    defect_quantity   = models.PositiveIntegerField('Yaroqsiz', default=0)
    cost              = models.DecimalField('Narxi', max_digits=12, decimal_places=2, default=0)

    return_to_stage = models.CharField(
        'Qaytish bosqichi',
        max_length=20,
        choices=ReturnStage.choices,
        help_text='Tashqi ishlov tugagach qaysi bo\'limga qaytadi',
    )

    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Yuboruvchi',
        related_name='outsource_sent',
        blank=True,
        null=True,
    )
    note    = models.TextField('Izoh', blank=True)
    sent_at     = models.DateTimeField('Yuborilgan vaqt', blank=True, null=True)
    received_at = models.DateTimeField('Qaytib kelgan vaqt', blank=True, null=True)
    created_at  = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at  = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tashqi ishlov'
        verbose_name_plural = 'Tashqi ishlovlar'

    def __str__(self):
        return f'{self.order.name} — {self.contractor} ({self.get_status_display()})'


# ──────────────────────────────────────────────
#  8. SIFAT NAZORATI  (har qanday bosqichda)
# ──────────────────────────────────────────────
class QualityControl(models.Model):

    class Stage(models.TextChoices):
        CASTING       = 'casting',       'Quyish bo\'limi'
        MONTAJ        = 'montaj',        'Montaj bo\'limi'
        HANGING       = 'hanging',       'Ilish bo\'limi'
        STONE_SETTING = 'stone_setting', 'Tosh qadash bo\'limi'
        PACKAGING     = 'packaging',     'Upakovka bo\'limi'
        WAREHOUSE     = 'warehouse',     'Ombor'
        OUTSOURCE     = 'outsource',     'Tashqi ishlov'

    class Result(models.TextChoices):
        PENDING  = 'pending',  'Tekshirilmoqda'
        PASSED   = 'passed',   'O\'tdi'
        PARTIAL  = 'partial',  'Qisman o\'tdi'
        FAILED   = 'failed',   'O\'tmadi'

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Buyurtma',
        related_name='quality_checks',
    )
    stage  = models.CharField('Bosqich', max_length=20, choices=Stage.choices)
    result = models.CharField('Natija', max_length=20, choices=Result.choices, default=Result.PENDING)

    checked_quantity = models.PositiveIntegerField('Tekshirilgan', default=0)
    passed_quantity  = models.PositiveIntegerField('Yaroqli', default=0)
    defect_quantity  = models.PositiveIntegerField('Yaroqsiz', default=0)
    defect_reason    = models.TextField('Nuqson sababi', blank=True)

    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Nazoratchi',
        related_name='quality_inspections',
        blank=True,
        null=True,
    )
    note       = models.TextField('Izoh', blank=True)
    checked_at = models.DateTimeField('Tekshirilgan vaqt', blank=True, null=True)
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sifat nazorati'
        verbose_name_plural = 'Sifat nazorati'

    def __str__(self):
        return f'{self.order.name} — {self.get_stage_display()} ({self.get_result_display()})'
