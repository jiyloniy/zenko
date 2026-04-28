from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "BOYASHMANAGER rolini va default foydalanuvchini yaratadi"

    def handle(self, *args, **options):
        from apps.users.models import Role, User

        role, created = Role.objects.get_or_create(
            name='BOYASHMANAGER',
            defaults={'description': "Bo'yash bo'limi menejeri"},
        )
        if created:
            self.stdout.write(self.style.SUCCESS("BOYASHMANAGER roli yaratildi."))
        else:
            self.stdout.write("BOYASHMANAGER roli allaqachon mavjud.")

        if not User.objects.filter(username='boyashmanager').exists():
            u = User(username='boyashmanager')
            u.set_password('boyash12345')
            u.name = "Bo'yash Menejer"
            u.role = role
            u.save()
            self.stdout.write(self.style.SUCCESS(
                "Foydalanuvchi yaratildi: boyashmanager / boyash12345"
            ))
        else:
            self.stdout.write("boyashmanager foydalanuvchisi allaqachon mavjud.")
