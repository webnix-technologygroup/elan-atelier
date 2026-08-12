from __future__ import annotations

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from studio.models import Booking, Customer, RescheduleRequest, Service, TeamMember

from .availability import slot_is_available
from .notifications import send_notification


def _notify(
    booking: Booking,
    kind: str,
    text: str,
    dedupe_key: str,
    *,
    notify_admin: bool = False,
) -> None:
    if booking.email:
        send_notification(
            kind=kind,
            recipient=booking.email,
            text=text,
            booking=booking,
            dedupe_key=dedupe_key,
            notify_admin=notify_admin,
        )


@transaction.atomic
def create_booking(
    *,
    service_id: int,
    master_id: int,
    starts_at: datetime,
    customer: Customer,
    message: str = "",
    source: str = "website",
) -> Booking:
    master = TeamMember.objects.select_for_update().get(
        pk=master_id,
        is_active=True,
        online_booking=True,
    )
    service = Service.objects.get(pk=service_id, is_active=True)
    if not master.services.filter(pk=service.pk).exists():
        raise ValidationError("Мастер не выполняет выбранную услугу.")
    if not slot_is_available(service, master, starts_at):
        raise ValidationError("Этот интервал уже недоступен.")
    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    return Booking.objects.create(
        customer=customer,
        name=customer.name,
        phone=customer.phone_normalized,
        phone_normalized=customer.phone_normalized,
        email=customer.email,
        service=service,
        master=master,
        preferred_date=starts_at.date(),
        starts_at=starts_at,
        ends_at=ends_at,
        duration_minutes=service.duration_minutes,
        buffer_before_minutes=service.buffer_before,
        buffer_after_minutes=service.buffer_after,
        price=service.price_from,
        message=message,
        source=source,
    )


def confirm_booking(booking: Booking) -> Booking:
    if booking.status != "pending":
        raise ValidationError("Подтвердить можно только новую запись.")
    booking.status = "confirmed"
    booking.confirmed_at = timezone.now()
    booking.save(update_fields=["status", "confirmed_at", "updated_at"])
    _notify(
        booking,
        "booking_confirmed",
        f"Запись #{booking.pk} подтверждена.",
        f"confirmed:{booking.pk}",
    )
    return booking


def complete_booking(booking: Booking) -> Booking:
    if booking.status not in {"confirmed", "in_progress"}:
        raise ValidationError("Завершить можно только подтверждённую запись.")
    booking.status = "completed"
    booking.save(update_fields=["status", "updated_at"])
    return booking


def mark_no_show(booking: Booking) -> Booking:
    if booking.status not in Booking.ACTIVE_STATUSES:
        raise ValidationError("Статус записи уже закрыт.")
    booking.status = "no_show"
    booking.save(update_fields=["status", "updated_at"])
    return booking


def cancel_booking(
    booking: Booking,
    *,
    reason: str,
    by_client: bool = True,
) -> Booking:
    if by_client and not booking.can_cancel:
        raise ValidationError("Эту запись уже нельзя отменить.")
    if not by_client and booking.status not in Booking.ACTIVE_STATUSES:
        raise ValidationError("Запись уже закрыта.")
    booking.status = "cancelled_by_client" if by_client else "cancelled_by_admin"
    booking.cancelled_at = timezone.now()
    booking.cancellation_reason = reason
    booking.save(
        update_fields=[
            "status",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )
    _notify(
        booking,
        "booking_cancelled",
        f"Запись #{booking.pk} отменена. Причина: {reason}",
        f"cancelled:{booking.pk}:{booking.status}",
        notify_admin=by_client,
    )
    return booking


def create_reschedule_request(
    booking: Booking,
    customer: Customer,
    starts_at: datetime,
    comment: str = "",
) -> RescheduleRequest:
    if booking.customer_id != customer.pk:
        raise ValidationError("Запись не принадлежит клиенту.")
    if not booking.can_reschedule:
        raise ValidationError("Перенос для этой записи недоступен.")
    if not booking.master or not slot_is_available(
        booking.service,
        booking.master,
        starts_at,
        exclude_booking_id=booking.pk,
    ):
        raise ValidationError("Выбранный интервал недоступен.")
    request_obj = RescheduleRequest.objects.create(
        booking=booking,
        customer=customer,
        requested_starts_at=starts_at,
        comment=comment,
    )
    booking.reschedule_requested = True
    booking.save(update_fields=["reschedule_requested", "updated_at"])
    _notify(
        booking,
        "reschedule_requested",
        f"Создан запрос переноса записи #{booking.pk} на {timezone.localtime(starts_at):%d.%m.%Y %H:%M}.",
        f"reschedule-requested:{request_obj.pk}",
        notify_admin=True,
    )
    return request_obj


@transaction.atomic
def approve_reschedule_request(request_obj: RescheduleRequest) -> RescheduleRequest:
    request_obj = (
        RescheduleRequest.objects.select_for_update()
        .select_related(
            "booking__service",
            "booking__master",
            "customer",
        )
        .get(pk=request_obj.pk)
    )
    if request_obj.status != "pending":
        raise ValidationError("Запрос уже обработан.")
    booking = Booking.objects.select_for_update().get(pk=request_obj.booking_id)
    master = TeamMember.objects.select_for_update().get(
        pk=booking.master_id,
        is_active=True,
        online_booking=True,
    )
    service = Service.objects.get(pk=booking.service_id, is_active=True)
    if not master.services.filter(pk=service.pk).exists() or not slot_is_available(
        service,
        master,
        request_obj.requested_starts_at,
        exclude_booking_id=booking.pk,
    ):
        raise ValidationError("Новый интервал уже недоступен.")
    old_value = timezone.localtime(booking.starts_at).strftime("%d.%m.%Y %H:%M")
    booking.starts_at = request_obj.requested_starts_at
    booking.ends_at = booking.starts_at + timedelta(minutes=booking.duration_minutes)
    booking.preferred_date = timezone.localtime(booking.starts_at).date()
    booking.reschedule_requested = False
    booking.admin_note = (booking.admin_note + f"\nПеренос с {old_value}.").strip()
    booking.save()
    request_obj.status = "approved"
    request_obj.processed_at = timezone.now()
    request_obj.save(update_fields=["status", "processed_at"])
    _notify(
        booking,
        "reschedule_approved",
        f"Перенос записи #{booking.pk} подтверждён: {timezone.localtime(booking.starts_at):%d.%m.%Y %H:%M}.",
        f"reschedule-approved:{request_obj.pk}",
        notify_admin=True,
    )
    return request_obj


def reject_reschedule_request(
    request_obj: RescheduleRequest,
    *,
    admin_note: str = "",
) -> RescheduleRequest:
    if request_obj.status != "pending":
        raise ValidationError("Запрос уже обработан.")
    request_obj.status = "rejected"
    request_obj.processed_at = timezone.now()
    request_obj.admin_note = admin_note
    request_obj.save(update_fields=["status", "processed_at", "admin_note"])
    booking = request_obj.booking
    booking.reschedule_requested = False
    booking.save(update_fields=["reschedule_requested", "updated_at"])
    _notify(
        booking,
        "reschedule_rejected",
        f"Запрос переноса записи #{booking.pk} отклонён.",
        f"reschedule-rejected:{request_obj.pk}",
    )
    return request_obj


request_reschedule = create_reschedule_request
