from __future__ import annotations

from datetime import date, datetime, timedelta

from django.utils import timezone

from studio.models import (
    Booking,
    MasterSchedule,
    MasterTimeOff,
    Service,
    SpecialWorkingDay,
    TeamMember,
)

STEP_MINUTES = 30
BOOKING_DEPTH_DAYS = 60


def aware(day: date, value) -> datetime:
    return timezone.make_aware(
        datetime.combine(day, value),
        timezone.get_current_timezone(),
    )


def suitable_masters(service: Service):
    return TeamMember.objects.filter(
        is_active=True,
        online_booking=True,
        services=service,
    ).distinct()


def get_available_slots(
    service: Service,
    master: TeamMember | None,
    day: date,
    *,
    now: datetime | None = None,
    exclude_booking_id: int | None = None,
) -> list[dict]:
    """Calculate slots using both new-service and existing-booking buffers."""
    now = now or timezone.now()
    today = timezone.localdate(now)
    if not service.is_active or not today <= day <= today + timedelta(
        days=BOOKING_DEPTH_DAYS
    ):
        return []
    if master and (
        not master.is_active
        or not master.online_booking
        or not master.services.filter(pk=service.pk).exists()
    ):
        return []

    result: list[dict] = []
    masters = [master] if master else suitable_masters(service)
    for person in masters:
        special = SpecialWorkingDay.objects.filter(master=person, date=day).first()
        schedule = None
        if not special:
            schedule = MasterSchedule.objects.filter(
                master=person,
                weekday=day.weekday(),
                is_active=True,
            ).first()
        if special:
            if not special.is_working or not special.start_time or not special.end_time:
                continue
            start_time = special.start_time
            end_time = special.end_time
            break_start = special.break_start
            break_end = special.break_end
        elif schedule:
            start_time = schedule.start_time
            end_time = schedule.end_time
            break_start = schedule.break_start
            break_end = schedule.break_end
        else:
            continue

        shift_start = aware(day, start_time)
        shift_end = aware(day, end_time)
        time_off = list(
            MasterTimeOff.objects.filter(
                master=person,
                starts_at__lt=shift_end,
                ends_at__gt=shift_start,
            )
        )
        bookings = Booking.objects.filter(
            master=person,
            status__in=Booking.ACTIVE_STATUSES,
            starts_at__lt=shift_end,
            ends_at__gt=shift_start,
        )
        if exclude_booking_id:
            bookings = bookings.exclude(pk=exclude_booking_id)
        bookings = list(bookings)

        cursor = shift_start + timedelta(minutes=service.buffer_before)
        latest_start = shift_end - timedelta(
            minutes=service.duration_minutes + service.buffer_after
        )
        while cursor <= latest_start:
            ends_at = cursor + timedelta(minutes=service.duration_minutes)
            occupied_start = cursor - timedelta(minutes=service.buffer_before)
            occupied_end = ends_at + timedelta(minutes=service.buffer_after)
            unavailable = cursor <= now
            if break_start and break_end:
                unavailable |= occupied_start < aware(
                    day, break_end
                ) and occupied_end > aware(day, break_start)
            unavailable |= any(
                block.all_day
                or (occupied_start < block.ends_at and occupied_end > block.starts_at)
                for block in time_off
            )
            unavailable |= any(
                booking.occupied_starts_at
                and occupied_start < booking.occupied_ends_at
                and occupied_end > booking.occupied_starts_at
                for booking in bookings
            )
            if not unavailable:
                result.append(
                    {
                        "time": cursor.strftime("%H:%M"),
                        "starts_at": cursor,
                        "ends_at": ends_at,
                        "master_id": person.pk,
                        "master_name": person.name,
                    }
                )
            cursor += timedelta(minutes=STEP_MINUTES)

    if master:
        return result
    unique: dict[str, dict] = {}
    for slot in sorted(result, key=lambda item: (item["time"], item["master_id"])):
        unique.setdefault(slot["time"], slot)
    return list(unique.values())


def nearest_available_dates(
    service: Service,
    master: TeamMember | None,
    start: date,
    limit: int = 3,
) -> list[str]:
    dates: list[str] = []
    for offset in range(1, BOOKING_DEPTH_DAYS + 1):
        candidate = start + timedelta(days=offset)
        if candidate > timezone.localdate() + timedelta(days=BOOKING_DEPTH_DAYS):
            break
        if get_available_slots(service, master, candidate):
            dates.append(candidate.isoformat())
            if len(dates) == limit:
                break
    return dates


def slot_is_available(
    service: Service,
    master: TeamMember,
    starts_at: datetime,
    *,
    exclude_booking_id: int | None = None,
) -> bool:
    return any(
        slot["starts_at"] == starts_at
        for slot in get_available_slots(
            service,
            master,
            timezone.localtime(starts_at).date(),
            exclude_booking_id=exclude_booking_id,
        )
    )
