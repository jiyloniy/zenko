from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('boyash', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BoyashVishilka',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nomi', models.CharField(max_length=200, verbose_name='Nomi')),
                ('quantity', models.PositiveIntegerField(
                    default=1,
                    help_text='Masalan: 25 parlik vishilka uchun 25 kiriting',
                    verbose_name='Par soni (bir vishilkada)',
                )),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Vishilka',
                'verbose_name_plural': 'Vishilkalar',
                'ordering': ['quantity', 'nomi'],
            },
        ),
        # Remove old par_soni field, add vishilka FK
        migrations.RemoveField(
            model_name='boyashjarayonlog',
            name='par_soni',
        ),
        migrations.AddField(
            model_name='boyashjarayonlog',
            name='vishilka',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='loglar',
                to='boyash.boyashvishilka',
                verbose_name='Vishilka',
            ),
        ),
        migrations.AlterField(
            model_name='boyashjarayonlog',
            name='vishilka_soni',
            field=models.PositiveIntegerField(
                default=1,
                verbose_name="Bo'yalgan vishilka soni",
            ),
        ),
    ]
