from django.conf import settings
from django.db import models


class Document(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_documents"
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Grant(models.Model):
    class Level(models.TextChoices):
        READ = "read", "Read"
        EDIT = "edit", "Edit"

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="grants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grants"
    )
    level = models.CharField(max_length=10, choices=Level.choices)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "user")


from django.utils import timezone


class AuditEntry(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    actor_name = models.CharField(max_length=150)
    action = models.CharField(max_length=30)
    document_id = models.IntegerField(null=True, blank=True)
    document_name = models.CharField(max_length=255, blank=True)
    outcome = models.CharField(max_length=10)
    detail = models.CharField(max_length=500, blank=True)
    prev_hash = models.CharField(max_length=64)
    entry_hash = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Audit entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit entries are append-only.")
