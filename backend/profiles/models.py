import uuid

from django.conf import settings
from django.db import models


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # NFR-1: random UUID
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    major = models.CharField(max_length=100)
    credit_limit = models.PositiveSmallIntegerField()
    target_term = models.CharField(max_length=20)
    completed_courses = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile({self.user})'