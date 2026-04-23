from django.db import models


class Stanok(models.Model):
    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Faol'
        REPAIR   = 'repair',   "Ta'mirda"
        INACTIVE = 'inactive', 'Faol emas'

    name   = models.CharField('Nomi', max_length=200)
    status = models.CharField('Holat', max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name        = 'Stanok'
        verbose_name_plural = 'Stanoklar'
        ordering            = ['name']

    def __str__(self):
        return self.name
