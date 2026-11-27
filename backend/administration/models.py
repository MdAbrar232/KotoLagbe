from django.conf import settings
from django.db import models


class AdminActivityLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="admin_activity_logs")
    action = models.CharField(max_length=40)
    entity = models.CharField(max_length=40)
    entity_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.actor or 'Unknown admin'}: {self.action} {self.entity} {self.entity_id}"


def record_activity(request, action_name, entity, obj, summary):
    AdminActivityLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action_name,
        entity=entity,
        entity_id=str(getattr(obj, "pk", "")),
        summary=summary[:255],
    )
