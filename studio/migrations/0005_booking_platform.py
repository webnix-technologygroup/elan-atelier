import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def prepare_existing(apps, schema_editor):
    TeamMember = apps.get_model("studio", "TeamMember")
    Booking = apps.get_model("studio", "Booking")
    from django.utils.text import slugify

    used = set()
    for item in TeamMember.objects.all():
        base = slugify(item.name, allow_unicode=False) or f"master-{item.pk}"
        value = base
        index = 2
        while value in used:
            value = f"{base}-{index}"
            index += 1
        used.add(value)
        item.slug = value
        item.save(update_fields=["slug"])
    mapping = {"new": "pending", "done": "completed", "cancelled": "cancelled_by_admin"}
    for item in Booking.objects.all():
        item.status = mapping.get(item.status, item.status)
        item.phone_normalized = "+" + "".join(c for c in item.phone if c.isdigit())
        item.duration_minutes = 60
        item.save(update_fields=["status", "phone_normalized", "duration_minutes"])


class Migration(migrations.Migration):
    dependencies = [("studio", "0004_content_management")]
    operations = [
        migrations.AlterField(
            model_name="siteasset",
            name="file",
            field=models.ImageField(
                blank=True, upload_to="site/", verbose_name="Изображение"
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="category",
            field=models.CharField(
                default="Салон", max_length=80, verbose_name="Категория"
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="short_description",
            field=models.CharField(
                blank=True, max_length=260, verbose_name="Короткое описание"
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="price_from",
            field=models.PositiveIntegerField(default=0, verbose_name="Цена от"),
        ),
        migrations.AddField(
            model_name="service",
            name="price_to",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Цена до"
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="duration_minutes",
            field=models.PositiveSmallIntegerField(
                default=60, verbose_name="Длительность, минут"
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="buffer_before",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Буфер до"),
        ),
        migrations.AddField(
            model_name="service",
            name="buffer_after",
            field=models.PositiveSmallIntegerField(
                default=10, verbose_name="Буфер после"
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="image",
            field=models.ImageField(blank=True, upload_to="services/"),
        ),
        migrations.AddField(
            model_name="service",
            name="fallback_image",
            field=models.CharField(blank=True, default="details.svg", max_length=120),
        ),
        migrations.AddField(
            model_name="service",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Активна"),
        ),
        migrations.AddField(
            model_name="service",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="service",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="service",
            name="uploaded_icon",
            field=models.ImageField(blank=True, upload_to="services/"),
        ),
        migrations.AddField(
            model_name="teammember",
            name="slug",
            field=models.SlugField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="teammember",
            name="specialization",
            field=models.CharField(
                blank=True, max_length=160, verbose_name="Специализация"
            ),
        ),
        migrations.AddField(
            model_name="teammember",
            name="bio_full",
            field=models.TextField(blank=True, verbose_name="Подробная биография"),
        ),
        migrations.AddField(
            model_name="teammember",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="teammember",
            name="phone",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="teammember",
            name="online_booking",
            field=models.BooleanField(default=True, verbose_name="Онлайн-запись"),
        ),
        migrations.AddField(
            model_name="teammember",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="teammember",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="teammember",
            name="uploaded_image",
            field=models.ImageField(blank=True, upload_to="team/"),
        ),
        migrations.AddField(
            model_name="teammember",
            name="services",
            field=models.ManyToManyField(
                blank=True, related_name="masters", to="studio.service"
            ),
        ),
        migrations.CreateModel(
            name="Customer",
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
                (
                    "phone_normalized",
                    models.CharField(blank=True, db_index=True, max_length=24),
                ),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("consent", models.BooleanField(default=False)),
                ("consent_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"verbose_name": "клиент", "verbose_name_plural": "Клиенты"},
        ),
        migrations.CreateModel(
            name="MasterSchedule",
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
                (
                    "weekday",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Понедельник"),
                            (1, "Вторник"),
                            (2, "Среда"),
                            (3, "Четверг"),
                            (4, "Пятница"),
                            (5, "Суббота"),
                            (6, "Воскресенье"),
                        ]
                    ),
                ),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("break_start", models.TimeField(blank=True, null=True)),
                ("break_end", models.TimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "master",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="schedules",
                        to="studio.teammember",
                    ),
                ),
            ],
            options={
                "ordering": ["master", "weekday"],
                "unique_together": {("master", "weekday")},
            },
        ),
        migrations.CreateModel(
            name="MasterTimeOff",
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
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("reason", models.CharField(blank=True, max_length=200)),
                ("all_day", models.BooleanField(default=False)),
                (
                    "master",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="time_offs",
                        to="studio.teammember",
                    ),
                ),
            ],
            options={"ordering": ["-starts_at"]},
        ),
        migrations.CreateModel(
            name="SpecialWorkingDay",
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
                ("date", models.DateField()),
                ("is_working", models.BooleanField(default=True)),
                ("start_time", models.TimeField(blank=True, null=True)),
                ("end_time", models.TimeField(blank=True, null=True)),
                ("break_start", models.TimeField(blank=True, null=True)),
                ("break_end", models.TimeField(blank=True, null=True)),
                (
                    "master",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="special_days",
                        to="studio.teammember",
                    ),
                ),
            ],
            options={"unique_together": {("master", "date")}},
        ),
        migrations.CreateModel(
            name="LoginToken",
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
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("code_hash", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="login_tokens",
                        to="studio.customer",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="booking",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bookings",
                to="studio.customer",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="phone_normalized",
            field=models.CharField(blank=True, db_index=True, max_length=24),
        ),
        migrations.AddField(
            model_name="booking",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="booking",
            name="master",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="studio.teammember",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="starts_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="ends_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="duration_minutes",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="booking",
            name="price",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="booking", name="admin_note", field=models.TextField(blank=True)
        ),
        migrations.AddField(
            model_name="booking",
            name="source",
            field=models.CharField(
                choices=[
                    ("website", "Сайт"),
                    ("admin", "Администратор"),
                    ("repeat", "Повторная запись"),
                    ("demo", "Демо"),
                ],
                default="website",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="cancellation_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="reschedule_requested",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="booking",
            name="preferred_date",
            field=models.DateField(blank=True, null=True, verbose_name="Желаемая дата"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Ожидает подтверждения"),
                    ("confirmed", "Подтверждена"),
                    ("in_progress", "В работе"),
                    ("completed", "Завершена"),
                    ("cancelled_by_client", "Отменена клиентом"),
                    ("cancelled_by_admin", "Отменена администратором"),
                    ("no_show", "Не пришёл"),
                ],
                db_index=True,
                default="pending",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="faq",
            name="service",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="faqs",
                to="studio.service",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="image_alt",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="article",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="article",
            name="uploaded_image",
            field=models.ImageField(blank=True, upload_to="journal/"),
        ),
        migrations.RunPython(prepare_existing, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="teammember", name="slug", field=models.SlugField(unique=True)
        ),
        migrations.CreateModel(
            name="GalleryItem",
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
                ("title", models.CharField(max_length=140)),
                ("category", models.CharField(max_length=80)),
                ("image", models.ImageField(blank=True, upload_to="gallery/")),
                (
                    "fallback_image",
                    models.CharField(default="details.svg", max_length=120),
                ),
                ("alt", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("is_published", models.BooleanField(default=True)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                (
                    "master",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gallery_items",
                        to="studio.teammember",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gallery_items",
                        to="studio.service",
                    ),
                ),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Review",
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
                ("name", models.CharField(max_length=100)),
                ("rating", models.PositiveSmallIntegerField()),
                ("text", models.TextField()),
                ("date", models.DateField()),
                ("source", models.CharField(default="Демо", max_length=80)),
                ("is_published", models.BooleanField(default=True)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                (
                    "master",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviews",
                        to="studio.teammember",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviews",
                        to="studio.service",
                    ),
                ),
            ],
            options={"ordering": ["order", "-date"]},
        ),
        migrations.CreateModel(
            name="NotificationLog",
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
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("booking_created", "Создание записи"),
                            ("login", "Вход"),
                            ("reminder", "Напоминание"),
                            ("cancelled", "Отмена"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[("email", "Email"), ("telegram", "Telegram")],
                        max_length=20,
                    ),
                ),
                ("recipient", models.CharField(max_length=200)),
                ("text", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает"),
                            ("sent", "Отправлено"),
                            ("failed", "Ошибка"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                (
                    "dedupe_key",
                    models.CharField(
                        blank=True, max_length=160, null=True, unique=True
                    ),
                ),
                (
                    "booking",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notifications",
                        to="studio.booking",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(
                fields=["master", "starts_at", "ends_at"],
                name="studio_book_master__53a531_idx",
            ),
        ),
    ]
