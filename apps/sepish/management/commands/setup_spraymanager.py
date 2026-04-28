from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'SPRAYMANAGER rolini va default foydalanuvchini yaratadi'

    def handle(self, *args, **options):
        from apps.users.models import Role, User

        role, created = Role.objects.get_or_create(
            name='SPRAYMANAGER',
            defaults={'description': "Sepish bo'limi menejeri"},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('SPRAYMANAGER roli yaratildi.'))
        else:
            self.stdout.write('SPRAYMANAGER roli allaqachon mavjud.')

        if not User.objects.filter(username='spraymanager').exists():
            u = User(username='spraymanager')
            u.set_password('spray12345')
            u.name = 'Sepish Menejer'
            u.role = role
            u.save()
            self.stdout.write(self.style.SUCCESS(
                'Foydalanuvchi yaratildi: spraymanager / spray12345'
            ))
        else:
            self.stdout.write('spraymanager foydalanuvchisi allaqachon mavjud.')
