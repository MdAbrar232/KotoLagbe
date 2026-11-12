
from django.contrib import admin
from .models import UserProfile, StatusPost


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "user",
        "gender",
        "location",
    )

    search_fields = (
        "full_name",
        "user__username",
        "location",
    )


@admin.register(StatusPost)
class StatusPostAdmin(admin.ModelAdmin):
    list_display = (
        "author",
        "content",
        "created_at",
    )

    search_fields = (
        "author__username",
        "content",
    )

    readonly_fields = ("created_at",)
