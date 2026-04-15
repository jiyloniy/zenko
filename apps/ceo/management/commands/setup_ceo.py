from django.core.management.base import BaseCommand

from apps.users.models import Role, User


class Command(BaseCommand):
    help = 'CEO rolini va CEO foydalanuvchini yaratish'

    def handle(self, *args, **options):
        role, created = Role.objects.get_or_create(
            name='CEO',
            defaults={'description': 'Bosh direktor — to\'liq boshqaruv huquqi'},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('CEO roli yaratildi.'))
        else:
            self.stdout.write('CEO roli allaqachon mavjud.')

        if not User.objects.filter(username='ceo').exists():
            user = User(
                username='ceo',
                name='CEO Admin',
                is_staff=True,
                is_superuser=True,
                is_active=True,
                role=role,
            )
            user.set_password('ceo12345')
            user.save()
            self.stdout.write(self.style.SUCCESS(
                'CEO foydalanuvchi yaratildi: username=ceo, password=ceo12345'
            ))
        else:
            self.stdout.write('CEO foydalanuvchi allaqachon mavjud.')
