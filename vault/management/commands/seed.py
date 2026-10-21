import uuid
from django.conf import settings
from django.core.management.base import BaseCommand
from vault.models import Document, Permission, User

DEMO = [
    ("admin_demo", "admin", "Admin#Demo2026"),
    ("owner_demo", "owner", "Owner#Demo2026"),
    ("viewer_demo", "viewer", "Viewer#Demo2026"),
    ("viewer2_demo", "viewer", "Viewer2#Demo2026"),
]
SAMPLES = [
    ("salary-letter.txt", "HR", "Salary letter for the viewer", ["viewer_demo"]),
    ("private-contract.txt", "Legal", "Private contract, owner only", []),
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        users = {}
        for name, role, pw in DEMO:
            u, _ = User.objects.get_or_create(username=name, defaults={"role": role})
            u.role = role
            u.set_password(pw)
            if role == "admin":
                u.is_staff = u.is_superuser = True
            u.save()
            users[name] = u
        settings.PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
        owner = users["owner_demo"]
        for name, cat, text, shared in SAMPLES:
            d, _ = Document.objects.get_or_create(
                name=name, owner=owner,
                defaults={"category": cat, "stored_name": uuid.uuid4().hex, "size": len(text)})
            (settings.PRIVATE_DIR / d.stored_name).write_text(text)
            for s in shared:
                Permission.objects.get_or_create(
                    document=d, user=users[s], defaults={"granted_by": owner})
        self.stdout.write("Seeded demo users and documents")
