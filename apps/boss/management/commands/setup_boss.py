from django.core.management.base import BaseCommand

from apps.users.models import Role, User


class Command(BaseCommand):
    help = 'BOSS rolini va BOSS foydalanuvchini yaratish'

    def handle(self, *args, **options):
        role, created = Role.objects.get_or_create(
            name='BOSS',
            defaults={'description': 'Boss — barcha filiallarni boshqarish huquqi'},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('BOSS roli yaratildi.'))
        else:
            self.stdout.write('BOSS roli allaqachon mavjud.')

        if not User.objects.filter(username='boss').exists():
            user = User(
                username='boss',
                name='Boss Admin',
                is_staff=True,
                is_active=True,
                role=role,
            )
            user.set_password('boss12345')
            user.save()
            self.stdout.write(self.style.SUCCESS(
                'BOSS foydalanuvchi yaratildi: username=boss, password=boss12345'
            ))
        else:
            self.stdout.write('BOSS foydalanuvchi allaqachon mavjud.')
