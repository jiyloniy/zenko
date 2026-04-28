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
            name='Kraska',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='Kodi')),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('color_hex', models.CharField(default='#6B7280', max_length=7, verbose_name='Rang (hex)')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Kraska', 'verbose_name_plural': 'Kraskalar', 'ordering': ['code']},
        ),
        migrations.CreateModel(
            name='SepishJarayon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[('qabul_qilindi','Qabul qilindi'),('sepilmoqda','Sepilmoqda'),('sepildi','Sepildi'),('sepilmadi','Sepilmadi')],
                    default='qabul_qilindi', max_length=20, verbose_name='Holat',
                )),
                ('izoh', models.TextField(blank=True, verbose_name='Izoh / sabab')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sepish_jarayonlar', to=settings.AUTH_USER_MODEL, verbose_name='Yaratgan')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='sepish_jarayon', to='order.order', verbose_name='Buyurtma')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sepish_jarayon_updates', to=settings.AUTH_USER_MODEL, verbose_name="Oxirgi o'zgartirgan")),
            ],
            options={'verbose_name': 'Sepish jarayoni', 'verbose_name_plural': 'Sepish jarayonlari', 'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='SepishJarayonLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('smena', models.CharField(choices=[('kun','Kunduzgi smena'),('tun','Tungi smena')], default='kun', max_length=5, verbose_name='Smena')),
                ('par_soni', models.PositiveIntegerField(default=1, verbose_name='Sepilgan par soni')),
                ('kraska_gramm', models.PositiveIntegerField(default=0, verbose_name='Kraska (gramm)')),
                ('izoh', models.TextField(blank=True, verbose_name='Izoh')),
                ('sana', models.DateField(verbose_name='Sana')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sepish_log_yozuvlar', to=settings.AUTH_USER_MODEL, verbose_name="Qo'shgan")),
                ('jarayon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loglar', to='sepish.sepishjarayon', verbose_name='Sepish jarayoni')),
                ('kraska', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='loglar', to='sepish.kraska', verbose_name='Kraska')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sepish_log_updates', to=settings.AUTH_USER_MODEL, verbose_name='Tahrirlagan')),
            ],
            options={'verbose_name': 'Sepish log', 'verbose_name_plural': 'Sepish loglar', 'ordering': ['-sana', '-created_at']},
        ),
    ]
