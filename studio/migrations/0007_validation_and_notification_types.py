import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("studio", "0006_booking_buffers_and_reschedule")]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="rating",
            field=models.PositiveSmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ]
            ),
        ),
        migrations.AlterField(
            model_name="notificationlog",
            name="type",
            field=models.CharField(
                choices=[
                    ("booking_created", "Создание записи"),
                    ("booking_confirmed", "Подтверждение"),
                    ("booking_cancelled", "Отмена"),
                    ("reschedule_requested", "Запрос переноса"),
                    ("reschedule_approved", "Перенос подтверждён"),
                    ("reschedule_rejected", "Перенос отклонён"),
                    ("login", "Вход"),
                    ("reminder", "Напоминание"),
                ],
                max_length=30,
            ),
        ),
    ]
