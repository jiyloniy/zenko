from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('order', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BoyashJarayon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('qabul_qilindi', 'Qabul qilindi'),
                        ('boyalmoqda', "Bo'yalmoqda"),
                        ('boyaldi', "Bo'yaldi"),
                        ('boyalmadi', "Bo'yalmadi"),
                    ],
                    default='qabul_qilindi', max_length=20, verbose_name='Holat',
                )),
                ('izoh', models.TextField(blank=True, verbose_name='Izoh / sabab')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='boyash_jarayonlar',
                    to=settings.AUTH_USER_MODEL, verbose_name='Yaratgan',
                )),
                ('order', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='boyash_jarayon',
                    to='order.order', verbose_name='Buyurtma',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='boyash_jarayon_updates',
                    to=settings.AUTH_USER_MODEL, verbose_name="Oxirgi o'zgartirgan",
                )),
            ],
            options={
                'verbose_name': "Bo'yash jarayoni",
                'verbose_name_plural': "Bo'yash jarayonlari",
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='BoyashJarayonLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('smena', models.CharField(
                    choices=[('kun', 'Kunduzgi smena'), ('tun', 'Tungi smena')],
                    default='kun', max_length=5, verbose_name='Smena',
                )),
                ('vishilka_soni', models.PositiveIntegerField(
                    default=1,
                    help_text="Nechta vishilka bo'yaldi",
                    verbose_name="Bo'yalgan vishilka soni",
                )),
                ('par_soni', models.PositiveIntegerField(
                    default=25,
                    help_text='Bir vishilkada nechta par bor',
                    verbose_name='Par soni (bir vishilkada)',
                )),
                ('izoh', models.TextField(blank=True, verbose_name='Izoh')),
                ('sana', models.DateField(verbose_name='Sana')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='boyash_log_yozuvlar',
                    to=settings.AUTH_USER_MODEL, verbose_name="Qo'shgan",
                )),
                ('jarayon', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='loglar',
                    to='boyash.boyashjarayon', verbose_name="Bo'yash jarayoni",
                )),
            ],
            options={
                'verbose_name': "Bo'yash log",
                'verbose_name_plural': "Bo'yash loglar",
                'ordering': ['-sana', '-created_at'],
            },
        ),
    ]
