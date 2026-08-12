from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from studio.models import Booking
from studio.services.notifications import send_notification


class Command(BaseCommand):
    help = "Отправляет email-напоминания о ближайших записях без дублей"

    def handle(self, *args, **kwargs):
        start = timezone.now() + timedelta(hours=23)
        end = timezone.now() + timedelta(hours=25)
        count = 0
        for b in Booking.objects.filter(
            status__in=("pending", "confirmed"),
            starts_at__gte=start,
            starts_at__lte=end,
        ).exclude(email=""):
            if send_notification(
                kind="reminder",
                recipient=b.email,
                text=f"Напоминание: {b.service.title} завтра в {timezone.localtime(b.starts_at):%H:%M}",
                booking=b,
                dedupe_key=f"reminder24:{b.pk}:{b.starts_at.date()}",
            ):
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Отправлено напоминаний: {count}"))
