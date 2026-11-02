import uuid

from django.conf import settings
from django.db import models


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # NFR-1: random UUID
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    major = models.CharField(max_length=100, blank=True, default='')
    credit_limit = models.PositiveSmallIntegerField(null=True, blank=True)
    target_term = models.CharField(max_length=20, blank=True, default='')
    completed_courses = models.JSONField(default=list)
    profile_version = models.PositiveIntegerField(default=1)  # bumped on every PUT (US-03 AC2 staleness)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_ready(self):
        """Program, credit limit and target term are all set (DR-12)."""
        return bool(self.major and self.credit_limit and self.target_term)

    def __str__(self):
        return f'Profile({self.user})'