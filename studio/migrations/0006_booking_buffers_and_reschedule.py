import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("studio", "0005_booking_platform")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="buffer_before_minutes",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="booking",
            name="buffer_after_minutes",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="RescheduleRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("requested_starts_at", models.DateTimeField()),
                ("comment", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает"),
                            ("approved", "Подтверждён"),
                            ("rejected", "Отклонён"),
                            ("cancelled", "Отменён"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("admin_note", models.TextField(blank=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reschedule_requests",
                        to="studio.booking",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reschedule_requests",
                        to="studio.customer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=Q(("status", "pending")),
                        fields=("booking",),
                        name="one_pending_reschedule",
                    )
                ],
            },
        ),
    ]
