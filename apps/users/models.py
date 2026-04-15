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

    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'Hodim'
        verbose_name_plural = 'Hodimlar'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.name} ({self.username})'


