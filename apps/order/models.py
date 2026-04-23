from django.db import models
from django.conf import settings


class Brujka(models.Model):

    class CoatingType(models.TextChoices):
        SPRAY_ONLY      = 'spray_only',      'Faqat sepish'
        PAINT_ONLY      = 'paint_only',      'Faqat bo\'yash'
        SPRAY_AND_PAINT = 'spray_and_paint', 'Sepish va bo\'yash'

    name         = models.CharField('Nomi', max_length=255)
    image        = models.ImageField('Rasm', upload_to='brujka/%Y/%m/')
    color        = models.CharField('Rang (hex)', max_length=7, default='#C0A060')
    coating_type = models.CharField('Qoplama turi', max_length=20, choices=CoatingType.choices, default=CoatingType.SPRAY_ONLY)
    description  = models.TextField('Tavsif', blank=True)
    is_active    = models.BooleanField('Faol', default=True)
    created_at   = models.DateTimeField('Yaratilgan', auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Brujka'
        verbose_name_plural = 'Brujkalar'

    def __str__(self):
        return self.name


class Order(models.Model):

    class Status(models.TextChoices):
        NEW        = 'new',        'Yangi'
        ACCEPTED   = 'accepted',   'Qabul qilindi'
        IN_PROCESS = 'in_process', 'Ishlab chiqarilmoqda'
        READY      = 'ready',      'Tayyor'
        DELIVERED  = 'delivered',  'Topshirildi'
        CANCELLED  = 'cancelled',  'Bekor qilindi'

    class Priority(models.TextChoices):
        LOW    = 'low',    'Past'
        NORMAL = 'normal', 'Oddiy'
        HIGH   = 'high',   'Yuqori'
        URGENT = 'urgent', 'Shoshilinch'

    order_number = models.CharField('Buyurtma raqami', max_length=20, unique=True, blank=True)
    brujka       = models.ForeignKey(
        Brujka,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Brujka',
        related_name='orders',
    )
    name         = models.CharField('Buyurtma nomi', max_length=255)
    quantity     = models.PositiveIntegerField('Miqdori')
    image        = models.ImageField('Rasm', upload_to='orders/%Y/%m/', blank=True, null=True)
    deadline     = models.DateField('Tayyor bo\'lish sanasi')
    status       = models.CharField('Holati', max_length=20, choices=Status.choices, default=Status.NEW)
    priority     = models.CharField('Muhimlik darajasi', max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    note         = models.TextField('Izoh', blank=True)
    created_by   = models.ForeignKey(
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

    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.utils.crypto import get_random_string
            self.order_number = f"ORD{get_random_string(6, '0123456789')}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.deadline < timezone.now().date()
            and self.status not in (self.Status.DELIVERED, self.Status.CANCELLED)
        )
