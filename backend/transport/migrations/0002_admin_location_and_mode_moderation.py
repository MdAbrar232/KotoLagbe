from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("transport", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="transportmode",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="location",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="location_submissions", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="submitted_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="location",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                db_index=True, default="pending", max_length=8,
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE transport_location SET status = 'approved'",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
