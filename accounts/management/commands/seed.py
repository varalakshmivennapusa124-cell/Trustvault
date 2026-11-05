import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

USERS = [
    ("admin", "admin", "SEED_ADMIN_PASSWORD"),
    ("owner1", "owner", "SEED_OWNER_PASSWORD"),
    ("viewer1", "viewer", "SEED_VIEWER_PASSWORD"),
]


class Command(BaseCommand):
    help = "Create demo accounts (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()
        for username, role, env_name in USERS:
            password = os.environ.get(env_name)
            if not password:
                self.stdout.write(f"skip {username}: {env_name} not set")
                continue
            user, created = User.objects.get_or_create(
                username=username, defaults={"role": role}
            )
            user.role = role
            user.is_staff = role == "admin"
            user.is_superuser = role == "admin"
            user.set_password(password)
            user.save()
            self.stdout.write(f"{'created' if created else 'updated'} {username}")