
from django.conf import settings
from django.db import models


class UserProfile(models.Model):

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("non_binary", "Non-binary"),
        ("other", "Other"),
        ("prefer_not_to_say", "Prefer not to say"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    full_name = models.CharField(max_length=120, blank=True)

    gender = models.CharField(
        max_length=30,
        choices=GENDER_CHOICES,
        default="prefer_not_to_say"
    )

    location = models.CharField(max_length=120, blank=True)

    bio = models.CharField(
        max_length=300,
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.username


class StatusPost(models.Model):

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="status_posts"
    )

    content = models.CharField(max_length=500)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:40]}"
