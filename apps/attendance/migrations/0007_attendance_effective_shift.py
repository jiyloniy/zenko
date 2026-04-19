# Generated for effective_shift smart detection feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0006_attendance_actual_check_out_and_more'),
        ('users', '0005_remove_user_shifts_user_shift'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='effective_shift',
            field=models.ForeignKey(
                blank=True,
                help_text='Kelish vaqtiga qarab aniqlangan smena. Hodim boshqa smenaga kelsa ham shu yerda saqlanadi.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='attendances',
                to='users.shift',
                verbose_name='Aniqlangan smena',
            ),
        ),
    ]
