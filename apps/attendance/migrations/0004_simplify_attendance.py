# Generated manually — davomatni soddalashtirish (smena yozuvdan olib tashlanadi).

from django.db import migrations, models


def forwards_status_cleanup(apps, schema_editor):
    Attendance = apps.get_model('attendance', 'Attendance')
    for row in Attendance.objects.exclude(status__in=('present', 'late', 'absent')):
        row.status = 'present'
        row.save(update_fields=['status'])


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0003_add_photo_field'),
    ]

    operations = [
        migrations.RunPython(forwards_status_cleanup, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='attendance',
            name='shift',
        ),
        migrations.RemoveField(
            model_name='attendance',
            name='is_overtime',
        ),
        migrations.AlterField(
            model_name='attendance',
            name='status',
            field=models.CharField(
                choices=[
                    ('present', 'Vaqtida keldi'),
                    ('late', 'Kechikdi'),
                    ('absent', 'Kelmadi'),
                ],
                default='present',
                max_length=20,
                verbose_name='Holat',
            ),
        ),
    ]
