import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ceo', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Migrate existing SalarySettings rows into HourlyRateHistory
        migrations.CreateModel(
            name='HourlyRateHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hourly_rate', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name="Soatlik stavka (so'm)")),
                ('effective_from', models.DateField(help_text='Shu sanadan boshlab ushbu stavka hisoblanadi.', verbose_name='Amal qilish boshlanishi')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rate_history', to=settings.AUTH_USER_MODEL, verbose_name='Hodim')),
            ],
            options={
                'verbose_name': 'Stavka tarixi',
                'verbose_name_plural': 'Stavka tarixi',
                'ordering': ['-effective_from'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='hourlyratehistory',
            unique_together={('user', 'effective_from')},
        ),
        # Copy existing SalarySettings → HourlyRateHistory with effective_from=2020-01-01
        migrations.RunSQL(
            sql="""
                INSERT INTO ceo_hourlyratehistory (user_id, hourly_rate, effective_from, note, created_at)
                SELECT user_id, hourly_rate, '2020-01-01', 'Migratsiya', updated_at
                FROM ceo_salarysettings
                WHERE hourly_rate > 0
                ON CONFLICT DO NOTHING;
            """,
            reverse_sql="DELETE FROM ceo_hourlyratehistory WHERE note = 'Migratsiya';",
        ),
        migrations.DeleteModel(
            name='SalarySettings',
        ),
    ]
