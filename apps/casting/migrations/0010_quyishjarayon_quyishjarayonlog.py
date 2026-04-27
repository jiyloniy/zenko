import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('casting', '0009_remove_quyishjarayon'),
        ('order', '0009_brujka_order_brujka'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='QuyishJarayon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('quyilmoqda', 'Quyilmoqda'),
                        ('quyib_bolindi', "Quyib bo'lindi"),
                        ('quyilmadi', 'Quyilmadi'),
                    ],
                    default='quyilmoqda', max_length=20, verbose_name='Quyish holati',
                )),
                ('izoh', models.TextField(blank=True, verbose_name='Izoh / sabab')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='quyish_jarayon',
                    to='order.order',
                    verbose_name='Buyurtma',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='quyish_jarayonlar',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Yaratgan',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='quyish_jarayon_updates',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Oxirgi o'zgartirgan",
                )),
            ],
            options={
                'verbose_name': 'Quyish jarayoni',
                'verbose_name_plural': 'Quyish jarayonlari',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='QuyishJarayonLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('miqdor', models.PositiveIntegerField(default=0, verbose_name='Quyilgan miqdor (dona)')),
                ('natija', models.CharField(
                    blank=True, null=True,
                    choices=[
                        ('tugatildi', 'Tugatildi'),
                        ('bekor_qilindi', 'Bekor qilindi'),
                    ],
                    max_length=20, verbose_name='Natija',
                )),
                ('izoh', models.TextField(blank=True, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('jarayon', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='loglar',
                    to='casting.quyishjarayon',
                    verbose_name='Quyish jarayoni',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Yozgan',
                )),
            ],
            options={
                'verbose_name': 'Quyish log',
                'verbose_name_plural': 'Quyish loglar',
                'ordering': ['-created_at'],
            },
        ),
    ]
