import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [("admin", "Admin"), ("owner", "Owner"), ("viewer", "Viewer")]
    role = models.CharField(max_length=10, choices=ROLES, default="viewer")


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="documents")
    stored_name = models.CharField(max_length=64)
    size = models.BigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)


class Permission(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="grants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    can_read = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "user")


class AuditLog(models.Model):
    time = models.DateTimeField()
    user_id = models.IntegerField(null=True)
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=30)
    document_id = models.UUIDField(null=True)
    result = models.CharField(max_length=10)
    detail = models.CharField(max_length=300, blank=True)
    ip = models.GenericIPAddressField(null=True)
    prev_hash = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("Audit log is append-only")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit log is append-only")