from django.core.management.base import BaseCommand
from apps.users.models import Role, User


class Command(BaseCommand):
    help = 'ATTACHMANAGER rolini va foydalanuvchisini yaratadi'

    def handle(self, *args, **options):
        role, created = Role.objects.get_or_create(
            name='ATTACHMANAGER',
            defaults={'description': 'Ilish bo\'limi menejeri — ilish jarayonlarini boshqarish huquqi'},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('ATTACHMANAGER roli yaratildi.'))
        else:
            self.stdout.write('ATTACHMANAGER roli allaqachon mavjud.')

        user, u_created = User.objects.get_or_create(
            username='attachmanager',
            defaults={
                'name':  'Ilish Menejeri',
                'role':  role,
            },
        )
        if u_created:
            user.set_password('attach12345')
            user.save()
            self.stdout.write(self.style.SUCCESS(
                'Foydalanuvchi yaratildi: attachmanager / attach12345'
            ))
        else:
            self.stdout.write('attachmanager foydalanuvchisi allaqachon mavjud.')
