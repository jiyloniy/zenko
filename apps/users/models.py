from django.contrib.auth.models import AbstractUser
from django.db import models


class Branch(models.Model):
    """Filiallar — har bir filial alohida boshqariladi."""

    name = models.CharField('Nomi', max_length=200, unique=True)
    address = models.CharField('Manzil', max_length=300, blank=True)
    phone = models.CharField('Telefon', max_length=20, blank=True)
    is_active = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Filial'
        verbose_name_plural = 'Filiallar'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    """Bo'limlar — hodim qaysi bo'limda ishlashi."""

    name = models.CharField('Nomi', max_length=150)
    description = models.TextField('Tavsif', blank=True)
    branch = models.ForeignKey(
        Branch,
        verbose_name='Filial',
        on_delete=models.PROTECT,
        related_name='departments',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bo\'lim'
        verbose_name_plural = 'Bo\'limlar'
        ordering = ['name']
        unique_together = ['name', 'branch']

    def __str__(self):
        return self.name


class Role(models.Model):
    """Foydalanuvchi rollari. Admin paneldan qo'shiladi."""

    name = models.CharField('Nomi', max_length=100, unique=True)
    description = models.TextField('Tavsif', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Rollar'
        ordering = ['name']

    def __str__(self):
        return self.name


class Shift(models.Model):
    """Ish smenalari — kunduzgi, tungi, kechki va h.k."""

    name = models.CharField('Nomi', max_length=100)
    start_time = models.TimeField('Boshlanish vaqti')
    end_time = models.TimeField('Tugash vaqti')
    break_start = models.TimeField('Tanaffus boshlanishi', null=True, blank=True)
    break_end = models.TimeField('Tanaffus tugashi', null=True, blank=True)
    description = models.TextField('Tavsif', blank=True)
    branch = models.ForeignKey(
        Branch,
        verbose_name='Filial',
        on_delete=models.PROTECT,
        related_name='shifts',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Smena'
        verbose_name_plural = 'Smenalar'
        ordering = ['start_time']
        unique_together = ['name', 'branch']

    def __str__(self):
        return f'{self.name} ({self.start_time:%H:%M}–{self.end_time:%H:%M})'


class VipStatusHistory(models.Model):
    """
    VIP statusining berilgan/olingan tarixi.
    Oylik hisobda shu tarixga qarab qaysi kunlar VIP sifatida hisoblanishi aniqlanadi.
    """
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='vip_history',
        verbose_name='Hodim',
    )
    is_vip = models.BooleanField('VIP holati', help_text='True=berildi, False=olindi')
    effective_from = models.DateField('Amal qilish boshlanishi')
    note = models.CharField('Izoh', max_length=255, blank=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vip_changes_made',
        verbose_name='O\'zgartirgan',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'VIP status tarixi'
        verbose_name_plural = 'VIP status tarixi'
        ordering = ['-effective_from', '-created_at']

    def __str__(self):
        action = 'berildi' if self.is_vip else 'olindi'
        return f'{self.user.name}: VIP {action} ({self.effective_from})'

    @classmethod
    def is_vip_on_date(cls, user, date):
        """Berilgan sanada hodim VIP bo'lganmi?"""
        entry = (
            cls.objects.filter(user=user, effective_from__lte=date)
            .order_by('-effective_from', '-created_at')
            .first()
        )
        if entry:
            return entry.is_vip
        # Tarix yo'q — User.is_vip maydoniga qaraymiz (backward compat)
        return getattr(user, 'is_vip', False)


class User(AbstractUser):
    """
    Custom User model.
    Login: username + password
    Har bir hodim bitta rolda, bitta bo'limda, bir yoki bir nechta smenada ishlaydi.
    """

    first_name = None
    last_name = None
    email = None

    name = models.CharField('Ism', max_length=150)
    phone = models.CharField('Telefon raqam', max_length=20, blank=True)
    role = models.ForeignKey(
        Role,
        verbose_name='Rol',
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        Department,
        verbose_name='Bo\'lim',
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
    )
    shift = models.ForeignKey(
        Shift,
        verbose_name='Smena',
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        Branch,
        verbose_name='Filial',
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
    )
    is_vip = models.BooleanField(
        'VIP hodim',
        default=False,
        help_text=(
            'VIP hodim kunduzgi yoki kechki smenada ishlashi mumkin. '
            'Kelgan vaqtiga qarab smena aniqlanadi va o\'sha smenaning '
            'to\'liq soati maoshga qo\'shiladi (kech kelsa ham to\'liq smena oyligi beriladi).'
        ),
    )

    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'Hodim'
        verbose_name_plural = 'Hodimlar'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.name} ({self.username})'


