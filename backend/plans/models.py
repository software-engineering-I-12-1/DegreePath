import uuid

from django.conf import settings
from django.db import models


class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='plans')
    name = models.CharField(max_length=100)
    entries = models.JSONField(default=list)
    profile_version_at_gen = models.PositiveIntegerField()
    catalog_version_at_gen = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
