import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Service",
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
                ("slug", models.SlugField(unique=True)),
                ("title", models.CharField(max_length=120)),
                ("eyebrow", models.CharField(max_length=80)),
                ("description", models.TextField()),
                ("price", models.CharField(max_length=60)),
                ("duration", models.CharField(max_length=60)),
                ("icon", models.CharField(default="sparkle", max_length=40)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("is_featured", models.BooleanField(default=True)),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="TeamMember",
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
                ("name", models.CharField(max_length=120)),
                ("role", models.CharField(max_length=120)),
                ("bio", models.CharField(max_length=240)),
                ("experience", models.CharField(max_length=80)),
                ("image", models.CharField(max_length=120)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="Article",
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
                ("slug", models.SlugField(unique=True)),
                ("title", models.CharField(max_length=180)),
                ("excerpt", models.CharField(max_length=300)),
                ("category", models.CharField(max_length=80)),
                ("reading_time", models.PositiveSmallIntegerField(default=5)),
                ("image", models.CharField(default="look-1.svg", max_length=120)),
                ("body", models.TextField()),
                ("published_at", models.DateField()),
                ("is_published", models.BooleanField(default=True)),
            ],
            options={"ordering": ["-published_at"]},
        ),
        migrations.CreateModel(
            name="Booking",
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
                ("name", models.CharField(max_length=120, verbose_name="Имя")),
                ("phone", models.CharField(max_length=40, verbose_name="Телефон")),
                ("preferred_date", models.DateField(verbose_name="Желаемая дата")),
                ("message", models.TextField(blank=True, verbose_name="Комментарий")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "Новая"),
                            ("confirmed", "Подтверждена"),
                            ("done", "Завершена"),
                            ("cancelled", "Отменена"),
                        ],
                        default="new",
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                (
                    "visitor_token_hash",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        editable=False,
                        max_length=64,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="studio.service",
                        verbose_name="Услуга",
                    ),
                ),
            ],
            options={
                "verbose_name": "запись",
                "verbose_name_plural": "записи",
                "ordering": ["-created_at"],
            },
        ),
    ]
