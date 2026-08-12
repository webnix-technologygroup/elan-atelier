import hashlib
import re
from datetime import datetime, time, timedelta
from unittest.mock import patch
from urllib.error import URLError

from django import forms as django_forms
from django.core import mail
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import normalize_phone
from .models import (
    FAQ,
    Article,
    Booking,
    Customer,
    GalleryItem,
    LoginToken,
    MasterTimeOff,
    NotificationLog,
    RescheduleRequest,
    Review,
    Service,
    TeamMember,
)
from .services.availability import get_available_slots
from .services.bookings import (
    approve_reschedule_request,
    create_reschedule_request,
)
from .services.notifications import send_notification


class BookingPlatformTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_seed_demo_is_idempotent(self):
        models = (
            Service,
            TeamMember,
            FAQ,
            Article,
            GalleryItem,
            Review,
            Customer,
            Booking,
            RescheduleRequest,
            NotificationLog,
        )
        counts = tuple(model.objects.count() for model in models)
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(
            counts,
            tuple(model.objects.count() for model in models),
        )

    def test_pages_and_detail_pages_render(self):
        names = [
            "home",
            "services",
            "team",
            "gallery",
            "journal",
            "contacts",
            "booking",
            "privacy",
        ]
        for name in names:
            self.assertEqual(
                self.client.get(reverse(f"studio:{name}")).status_code, 200
            )
        self.assertEqual(
            self.client.get(
                reverse("studio:service_detail", args=[Service.objects.first().slug])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("studio:team_detail", args=[TeamMember.objects.first().slug])
            ).status_code,
            200,
        )

    def future_workday(self):
        day = timezone.localdate() + timedelta(days=2)
        while day.weekday() == 6:
            day += timedelta(days=1)
        return day

    def test_slots_respect_break_and_past(self):
        service = Service.objects.get(slug="haircut")
        master = service.masters.first()
        slots = get_available_slots(service, master, self.future_workday())
        self.assertTrue(slots)
        self.assertFalse(any(slot["time"] == "13:00" for slot in slots))
        self.assertEqual(
            get_available_slots(
                service, master, timezone.localdate() - timedelta(days=1)
            ),
            [],
        )

    def test_time_off_blocks_slots(self):
        service = Service.objects.get(slug="haircut")
        master = service.masters.first()
        day = self.future_workday()
        MasterTimeOff.objects.create(
            master=master,
            starts_at=timezone.make_aware(datetime.combine(day, time.min)),
            ends_at=timezone.make_aware(datetime.combine(day, time.max)),
            all_day=True,
        )
        self.assertEqual(get_available_slots(service, master, day), [])

    def test_existing_booking_blocks_and_cancel_frees_slot(self):
        service = Service.objects.get(slug="haircut")
        master = service.masters.first()
        day = self.future_workday()
        slot = get_available_slots(service, master, day)[0]
        booking = Booking.objects.create(
            name="Тест",
            phone="+38000000000",
            phone_normalized="+38000000000",
            email="slot@example.test",
            service=service,
            master=master,
            preferred_date=day,
            starts_at=slot["starts_at"],
            ends_at=slot["ends_at"],
            duration_minutes=service.duration_minutes,
            price=service.price_from,
        )
        self.assertNotIn(
            slot["time"],
            [item["time"] for item in get_available_slots(service, master, day)],
        )
        booking.status = "cancelled_by_client"
        booking.save(update_fields=["status"])
        self.assertIn(
            slot["time"],
            [item["time"] for item in get_available_slots(service, master, day)],
        )

    def test_slots_api_validation_and_master_filter(self):
        service = Service.objects.get(slug="haircut")
        day = self.future_workday()
        response = self.client.get(
            reverse("studio:available_slots"),
            {"service": service.slug, "date": day.isoformat(), "master": "any"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("slots", response.json())
        wrong = TeamMember.objects.exclude(services=service).first()
        response = self.client.get(
            reverse("studio:available_slots"),
            {"service": service.slug, "date": day.isoformat(), "master": wrong.pk},
        )
        self.assertEqual(response.status_code, 400)

    def test_magic_code_expiry_and_attempt_limit(self):
        customer = Customer.objects.first()
        expired = LoginToken.objects.create(
            customer=customer,
            token_hash="a" * 64,
            code_hash=hashlib.sha256(b"123456").hexdigest(),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(expired.valid)
        active = LoginToken.objects.create(
            customer=customer,
            token_hash="b" * 64,
            code_hash=hashlib.sha256(b"654321").hexdigest(),
            expires_at=timezone.now() + timedelta(minutes=5),
            attempts=5,
        )
        self.assertFalse(active.valid)

    def test_customer_cannot_open_foreign_booking(self):
        customer = Customer.objects.first()
        foreign = Booking.objects.exclude(customer=customer).first()
        session = self.client.session
        session["customer_id"] = customer.pk
        session.save()
        self.assertEqual(
            self.client.get(
                reverse("studio:booking_detail", args=[foreign.public_id])
            ).status_code,
            404,
        )

    def test_reminders_are_not_duplicated(self):
        booking = Booking.objects.filter(status__in=("pending", "confirmed")).first()
        booking.starts_at = timezone.now() + timedelta(hours=24)
        booking.ends_at = booking.starts_at + timedelta(
            minutes=booking.duration_minutes
        )
        booking.save()
        call_command("send_booking_reminders", verbosity=0)
        call_command("send_booking_reminders", verbosity=0)
        self.assertEqual(
            NotificationLog.objects.filter(type="reminder", booking=booking).count(), 1
        )

    def test_robots_sitemap_and_404(self):
        self.assertContains(
            self.client.get(reverse("studio:robots")), "Disallow: /cabinet/"
        )
        self.assertContains(self.client.get(reverse("studio:sitemap")), "/services/")
        self.assertEqual(self.client.get("/missing-page/").status_code, 404)


class SecurityRegressionTests(TestCase):

    def future_workday(self):
        day = timezone.localdate() + timedelta(days=2)
        while day.weekday() == 6:
            day += timedelta(days=1)
        return day

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_anonymous_cannot_manage_booking(self):
        booking = Booking.objects.exclude(customer=None).first()
        detail = reverse("studio:booking_detail", args=[booking.public_id])
        cancel = reverse("studio:cancel_booking", args=[booking.public_id])
        reschedule = reverse("studio:request_reschedule", args=[booking.public_id])
        self.assertEqual(self.client.get(detail).status_code, 302)
        status = booking.status
        self.assertEqual(self.client.post(cancel, {"reason": "Нет"}).status_code, 302)
        self.assertEqual(
            self.client.post(
                reschedule, {"date": timezone.localdate(), "time": "12:00"}
            ).status_code,
            302,
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, status)

    def test_customer_none_is_never_exposed(self):
        booking = Booking.objects.first()
        booking.customer = None
        booking.save(update_fields=["customer"])
        self.assertEqual(
            self.client.get(
                reverse("studio:booking_detail", args=[booking.public_id])
            ).status_code,
            302,
        )

    def test_other_customer_gets_404(self):
        booking = Booking.objects.exclude(customer=None).first()
        other = Customer.objects.exclude(pk=booking.customer_id).first()
        session = self.client.session
        session["customer_id"] = other.pk
        session.save()
        self.assertEqual(
            self.client.get(
                reverse("studio:booking_detail", args=[booking.public_id])
            ).status_code,
            404,
        )

    def test_logout_requires_post(self):
        self.assertEqual(
            self.client.get(reverse("studio:logout_customer")).status_code, 405
        )

    def test_existing_buffer_blocks_following_slots(self):
        service = Service.objects.get(slug="haircut")
        master = service.masters.first()
        day = self.future_workday()
        start = timezone.make_aware(datetime.combine(day, time(10, 30)))
        Booking.objects.create(
            name="Буфер",
            phone="+38000000000",
            phone_normalized="+38000000000",
            email="buffer@example.test",
            service=service,
            master=master,
            starts_at=start,
            ends_at=start + timedelta(minutes=90),
            duration_minutes=90,
            buffer_after_minutes=30,
            price=1800,
        )
        times = [slot["time"] for slot in get_available_slots(service, master, day)]
        self.assertNotIn("12:00", times)
        self.assertNotIn("12:15", times)


class PhoneNormalizationTests(SimpleTestCase):

    def test_supported_phone_formats(self):
        expected = "+380671234567"
        self.assertEqual(normalize_phone("+380671234567"), expected)
        self.assertEqual(normalize_phone("+38 (067) 123-45-67"), expected)
        self.assertEqual(normalize_phone("380 67 123 45 67"), expected)

    def test_short_phone_is_rejected(self):
        with self.assertRaises(django_forms.ValidationError):
            normalize_phone("+123")

    def test_long_phone_is_rejected(self):
        with self.assertRaises(django_forms.ValidationError):
            normalize_phone("+1234567890123456")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BookingEndToEndTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def find_slot(self):
        service = Service.objects.get(slug="haircut")
        master = service.masters.filter(is_active=True, online_booking=True).first()
        for offset in range(1, 30):
            day = timezone.localdate() + timedelta(days=offset)
            response = self.client.get(
                reverse("studio:available_slots"),
                {"service": service.pk, "master": master.pk, "date": day.isoformat()},
            )
            slots = response.json().get("slots", [])
            if slots:
                return (service, master, day, slots[0])
        self.fail("Демоданные не предоставили доступный слот")

    def test_full_booking_email_magic_link_and_ics(self):
        service, master, day, slot = self.find_slot()
        response = self.client.post(
            reverse("studio:booking"),
            {
                "service": service.pk,
                "master": master.pk,
                "date": day.isoformat(),
                "time": slot["time"],
                "selected_master": master.pk,
                "name": "Тестовый клиент",
                "phone": "+38 (067) 123-45-67",
                "email": "e2e@example.test",
                "message": "Проверка полного сценария",
                "consent": "on",
                "website": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get(email="e2e@example.test")
        self.assertEqual(booking.phone_normalized, "+380671234567")
        self.assertEqual(booking.service, service)
        self.assertEqual(booking.master, master)
        self.assertEqual(booking.duration_minutes, service.duration_minutes)
        self.assertEqual(booking.price, service.price_from)
        self.assertEqual(booking.buffer_before_minutes, service.buffer_before)
        self.assertEqual(booking.buffer_after_minutes, service.buffer_after)
        self.assertTrue(
            NotificationLog.objects.filter(
                booking=booking, type="booking_created"
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        self.assertIn("Вход в кабинет:", email_body)
        self.assertIn("Добавить в календарь:", email_body)
        magic_path = (
            email_body.split("Вход в кабинет: ", 1)[1]
            .splitlines()[0]
            .replace("http://testserver", "")
        )
        first = self.client.get(magic_path)
        self.assertEqual(first.status_code, 302)
        second = self.client.get(magic_path)
        self.assertEqual(second.status_code, 400)
        ics = self.client.get(reverse("studio:booking_ics", args=[booking.public_id]))
        self.assertEqual(ics.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", ics.content.decode())
        self.assertIn(str(booking.public_id), ics.content.decode())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RescheduleWorkflowTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_approve_reschedule_moves_booking(self):
        booking = Booking.objects.filter(
            status="confirmed", customer__isnull=False
        ).first()
        service = booking.service
        master = booking.master
        target = None
        for offset in range(2, 30):
            slots = get_available_slots(
                service, master, timezone.localdate() + timedelta(days=offset)
            )
            if slots:
                target = slots[0]["starts_at"]
                break
        self.assertIsNotNone(target)
        old_start = booking.starts_at
        request_obj = create_reschedule_request(booking, booking.customer, target)
        approve_reschedule_request(request_obj)
        booking.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, "approved")
        self.assertEqual(booking.starts_at, target)
        self.assertNotEqual(booking.starts_at, old_start)
        self.assertFalse(booking.reschedule_requested)


class TelegramNotificationTests(TestCase):

    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
    def test_disabled_telegram_does_not_fail(self):
        send_notification(
            kind="login", recipient="demo@example.test", text="test", notify_admin=True
        )
        self.assertEqual(NotificationLog.objects.filter(channel="telegram").count(), 0)

    @override_settings(TELEGRAM_BOT_TOKEN="secret-token", TELEGRAM_CHAT_ID="12345")
    @patch("studio.services.notifications.request.urlopen")
    def test_telegram_uses_bot_api_and_chat_id(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b"ok"
        send_notification(
            kind="login",
            recipient="demo@example.test",
            text="test",
            dedupe_key="tg-ok",
            notify_admin=True,
        )
        endpoint = urlopen.call_args.args[0]
        payload = urlopen.call_args.kwargs["data"].decode()
        self.assertIn("api.telegram.org/botsecret-token/sendMessage", endpoint)
        self.assertIn("chat_id=12345", payload)

    @override_settings(TELEGRAM_BOT_TOKEN="secret-token", TELEGRAM_CHAT_ID="12345")
    @patch(
        "studio.services.notifications.request.urlopen", side_effect=URLError("offline")
    )
    def test_telegram_failure_is_logged_without_token(self, _urlopen):
        send_notification(
            kind="login",
            recipient="demo@example.test",
            text="test",
            dedupe_key="tg-fail",
            notify_admin=True,
        )
        log = NotificationLog.objects.get(channel="telegram")
        self.assertEqual(log.status, "failed")
        self.assertNotIn("secret-token", log.error)


class FinalPassRegressionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_home_uses_active_master_count(self):
        active_count = TeamMember.objects.filter(is_active=True).count()
        inactive = TeamMember.objects.first()
        inactive.is_active = False
        inactive.save(update_fields=["is_active"])
        response = self.client.get(reverse("studio:home"))
        self.assertContains(response, str(active_count - 1))
        self.assertEqual(response.context["master_count"], active_count - 1)

    def test_reschedule_slots_excludes_current_but_blocks_other_booking_and_constraints(
        self,
    ):
        service = Service.objects.get(slug="haircut")
        master = service.masters.filter(is_active=True, online_booking=True).first()
        customer = Customer.objects.first()
        day = timezone.localdate() + timedelta(days=3)
        while not get_available_slots(service, master, day):
            day += timedelta(days=1)
        initial = get_available_slots(service, master, day)
        current_slot = initial[0]
        current = Booking.objects.create(
            customer=customer,
            name=customer.name,
            phone=customer.phone_normalized,
            phone_normalized=customer.phone_normalized,
            email=customer.email,
            service=service,
            master=master,
            preferred_date=day,
            starts_at=current_slot["starts_at"],
            ends_at=current_slot["ends_at"],
            duration_minutes=service.duration_minutes,
            buffer_before_minutes=service.buffer_before,
            buffer_after_minutes=service.buffer_after,
            price=service.price_from,
            status="confirmed",
        )
        session = self.client.session
        session["customer_id"] = customer.pk
        session.save()
        url = reverse("studio:reschedule_slots", args=[current.public_id])
        response = self.client.get(url, {"date": day.isoformat()})
        self.assertEqual(response.status_code, 200)
        returned = {slot["time"] for slot in response.json()["slots"]}
        self.assertIn(current_slot["time"], returned)

        blocker_slot = get_available_slots(service, master, day)[0]
        Booking.objects.create(
            customer=customer,
            name="Вторая запись",
            phone=customer.phone_normalized,
            phone_normalized=customer.phone_normalized,
            email=customer.email,
            service=service,
            master=master,
            preferred_date=day,
            starts_at=blocker_slot["starts_at"],
            ends_at=blocker_slot["ends_at"],
            duration_minutes=service.duration_minutes,
            buffer_before_minutes=service.buffer_before,
            buffer_after_minutes=service.buffer_after,
            price=service.price_from,
            status="confirmed",
        )
        returned = {
            slot["time"]
            for slot in self.client.get(url, {"date": day.isoformat()}).json()["slots"]
        }
        self.assertNotIn(blocker_slot["time"], returned)
        self.assertFalse(any(time_value == "13:00" for time_value in returned))

        free = get_available_slots(service, master, day, exclude_booking_id=current.pk)
        if free:
            blocked = free[-1]
            MasterTimeOff.objects.create(
                master=master,
                starts_at=blocked["starts_at"],
                ends_at=blocked["ends_at"],
                reason="Тест TimeOff",
            )
            returned = {
                slot["time"]
                for slot in self.client.get(url, {"date": day.isoformat()}).json()[
                    "slots"
                ]
            }
            self.assertNotIn(blocked["time"], returned)

        for invalid_day in (
            timezone.localdate() - timedelta(days=1),
            timezone.localdate() + timedelta(days=61),
        ):
            self.assertEqual(
                self.client.get(url, {"date": invalid_day.isoformat()}).status_code,
                400,
            )
        current.starts_at = timezone.now() + timedelta(hours=6)
        current.ends_at = current.starts_at + timedelta(
            minutes=current.duration_minutes
        )
        current.save(update_fields=["starts_at", "ends_at"])
        self.assertEqual(
            self.client.get(url, {"date": day.isoformat()}).status_code, 400
        )

    def test_foreign_reschedule_slots_returns_404(self):
        booking = Booking.objects.filter(customer__isnull=False).first()
        other = Customer.objects.exclude(pk=booking.customer_id).first()
        session = self.client.session
        session["customer_id"] = other.pk
        session.save()
        response = self.client.get(
            reverse("studio:reschedule_slots", args=[booking.public_id]),
            {"date": timezone.localdate().isoformat()},
        )
        self.assertEqual(response.status_code, 404)


class WizardInitialStepTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def post(self, **changes):
        service = Service.objects.get(slug="haircut")
        master = service.masters.filter(is_active=True, online_booking=True).first()
        data = {
            "service": service.pk,
            "master": master.pk,
            "date": "bad",
            "time": "10:00",
            "selected_master": master.pk,
            "name": "Клиент",
            "phone": "+380671234567",
            "email": "wizard@example.test",
            "message": "",
            "consent": "on",
            "website": "",
        }
        data.update(changes)
        return self.client.post(reverse("studio:booking"), data)

    def test_service_error_opens_step_one(self):
        self.assertEqual(self.post(service="").context["initial_step"], 1)

    def test_master_error_opens_step_two(self):
        self.assertEqual(
            self.post(master="invalid", date=timezone.localdate()).context[
                "initial_step"
            ],
            2,
        )

    def test_date_error_opens_step_three(self):
        self.assertEqual(self.post(date="bad").context["initial_step"], 3)

    def test_slot_error_opens_step_four(self):
        self.assertEqual(
            self.post(date=timezone.localdate(), time="").context["initial_step"], 4
        )

    def test_contact_error_opens_step_five(self):
        self.assertEqual(
            self.post(date=timezone.localdate(), name="").context["initial_step"], 5
        )


class ApiBoundaryTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_slots_reject_non_numeric_master(self):
        service = Service.objects.get(slug="haircut")
        response = self.client.get(
            reverse("studio:available_slots"),
            {"service": service.pk, "date": timezone.localdate(), "master": "abc"},
        )
        self.assertEqual(response.status_code, 400)

    def test_slots_reject_past_and_over_sixty_days(self):
        service = Service.objects.get(slug="haircut")
        for day in (
            timezone.localdate() - timedelta(days=1),
            timezone.localdate() + timedelta(days=61),
        ):
            response = self.client.get(
                reverse("studio:available_slots"),
                {"service": service.pk, "date": day, "master": "any"},
            )
            self.assertEqual(response.status_code, 400)

    def test_success_and_ics_require_owner_session(self):
        booking = Booking.objects.filter(customer__isnull=False).first()
        self.assertEqual(
            self.client.get(
                reverse("studio:booking_success", args=[booking.public_id])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("studio:booking_ics", args=[booking.public_id])
            ).status_code,
            404,
        )
        session = self.client.session
        session["customer_id"] = booking.customer_id
        session.save()
        self.assertEqual(
            self.client.get(
                reverse("studio:booking_success", args=[booking.public_id])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("studio:booking_ics", args=[booking.public_id])
            ).status_code,
            200,
        )


class FinalV6AccessAndSeoTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def endpoints(self, booking):
        return (
            reverse("studio:booking_success", args=[booking.public_id]),
            reverse("studio:booking_ics", args=[booking.public_id]),
        )

    def test_anonymous_cannot_open_customer_booking_on_both_endpoints(self):
        booking = Booking.objects.filter(customer__isnull=False).first()
        for url in self.endpoints(booking):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_anonymous_cannot_open_customerless_booking_on_both_endpoints(self):
        booking = Booking.objects.first()
        booking.customer = None
        booking.save(update_fields=["customer"])
        for url in self.endpoints(booking):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_foreign_customer_cannot_open_either_endpoint(self):
        booking = Booking.objects.filter(customer__isnull=False).first()
        other = Customer.objects.exclude(pk=booking.customer_id).first()
        session = self.client.session
        session["customer_id"] = other.pk
        session.save()
        for url in self.endpoints(booking):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_owner_opens_success_and_downloads_complete_ics(self):
        booking = Booking.objects.filter(customer__isnull=False).first()
        session = self.client.session
        session["customer_id"] = booking.customer_id
        session.save()
        success, calendar = self.endpoints(booking)
        self.assertEqual(self.client.get(success).status_code, 200)
        response = self.client.get(calendar)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/calendar", response["Content-Type"])
        self.assertIn("attachment;", response["Content-Disposition"])
        body = response.content.decode()
        for value in (
            "PRODID:",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "SUMMARY:",
            "DESCRIPTION:",
            "LOCATION:",
        ):
            self.assertIn(value, body)
        self.assertIn("\r\n", body)

    def test_unknown_uuid_is_404_on_both_endpoints(self):
        import uuid

        booking = Booking.objects.filter(customer__isnull=False).first()
        session = self.client.session
        session["customer_id"] = booking.customer_id
        session.save()
        missing = uuid.uuid4()
        for name in ("booking_success", "booking_ics"):
            self.assertEqual(
                self.client.get(reverse(f"studio:{name}", args=[missing])).status_code,
                404,
            )

    def test_bound_booking_form_preserves_values_and_invalidates_slot(self):
        service = Service.objects.get(slug="haircut")
        master = service.masters.filter(is_active=True, online_booking=True).first()
        day = timezone.localdate() + timedelta(days=2)
        data = {
            "service": service.pk,
            "master": master.pk,
            "date": day.isoformat(),
            "time": "00:01",
            "selected_master": master.pk,
            "name": "Сохранённое имя",
            "phone": "+380671234567",
            "email": "bound@example.test",
            "message": "Сохранённый комментарий",
            "consent": "on",
            "website": "",
        }
        response = self.client.post(reverse("studio:booking"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["initial_step"], 4)
        form = response.context["form"]
        for key in ("service", "master", "date", "name", "phone", "email", "message"):
            self.assertEqual(str(form[key].value()), str(data[key]))
        self.assertIn("time", form.errors)
        self.assertContains(response, 'data-initial-step="4"')

    def test_seo_json_ld_canonical_and_sitemap(self):
        import json

        article = Article.objects.filter(is_published=True).first()
        response = self.client.get(
            reverse("studio:article", args=[article.slug]) + "?utm=test"
        )
        html = response.content.decode()
        self.assertIn('property="og:type" content="article"', html)
        self.assertIn(article.title, html)
        canonical = re.search(r'<link rel="canonical" href="([^"]+)', html).group(1)
        self.assertNotIn("?", canonical)
        image = re.search(r'<meta property="og:image" content="([^"]+)', html).group(1)
        self.assertTrue(image.startswith("http"))
        payload = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
        ).group(1)
        data = json.loads(payload)
        self.assertEqual(data[0]["@type"], "Article")
        self.assertTrue(data[0]["headline"])
        sitemap = self.client.get(reverse("studio:sitemap")).content.decode()
        for forbidden in ("/admin/", "/api/", "/booking/", "/cabinet/", ".ics"):
            self.assertNotIn(forbidden, sitemap)
