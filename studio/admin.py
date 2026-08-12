from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import (
    FAQ,
    Article,
    Booking,
    Customer,
    GalleryItem,
    LoginToken,
    MasterSchedule,
    MasterTimeOff,
    NotificationLog,
    RescheduleRequest,
    Review,
    Service,
    SiteAsset,
    SiteText,
    SpecialWorkingDay,
    TeamMember,
)
from .services.bookings import (
    approve_reschedule_request,
    cancel_booking,
    complete_booking,
    confirm_booking,
    mark_no_show,
    reject_reschedule_request,
)


class ScheduleInline(admin.TabularInline):
    model = MasterSchedule
    extra = 0


class SpecialDayInline(admin.TabularInline):
    model = SpecialWorkingDay
    extra = 0


def run_booking_action(modeladmin, request, queryset, action):
    completed = 0
    for booking in queryset.select_related("service", "master", "customer"):
        try:
            action(booking)
        except ValidationError as error:
            modeladmin.message_user(
                request,
                f"#{booking.pk}: {error.messages[0]}",
                level=messages.WARNING,
            )
        else:
            completed += 1
    modeladmin.message_user(request, f"Обработано записей: {completed}.")


@admin.action(description="Подтвердить")
def confirm_action(modeladmin, request, queryset):
    run_booking_action(modeladmin, request, queryset, confirm_booking)


@admin.action(description="Завершить")
def complete_action(modeladmin, request, queryset):
    run_booking_action(modeladmin, request, queryset, complete_booking)


@admin.action(description="Отменить администратором")
def cancel_action(modeladmin, request, queryset):
    run_booking_action(
        modeladmin,
        request,
        queryset,
        lambda booking: cancel_booking(
            booking,
            reason="Отменено администратором",
            by_client=False,
        ),
    )


@admin.action(description="Не пришёл")
def no_show_action(modeladmin, request, queryset):
    run_booking_action(modeladmin, request, queryset, mark_no_show)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "contact",
        "service",
        "master",
        "starts_at",
        "status",
    )
    list_filter = ("status", "master", "service", "starts_at")
    search_fields = ("name", "phone", "email", "public_id")
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "confirmed_at",
        "cancelled_at",
    )
    actions = (confirm_action, complete_action, cancel_action, no_show_action)
    date_hierarchy = "starts_at"
    fieldsets = (
        ("Клиент", {"fields": ("customer", "name", "phone", "email")}),
        (
            "Визит",
            {
                "fields": (
                    "service",
                    "master",
                    "starts_at",
                    "ends_at",
                    "duration_minutes",
                    "buffer_before_minutes",
                    "buffer_after_minutes",
                    "price",
                    "status",
                )
            },
        ),
        (
            "Комментарии",
            {
                "fields": (
                    "message",
                    "admin_note",
                    "cancellation_reason",
                    "reschedule_requested",
                )
            },
        ),
        (
            "Система",
            {
                "fields": (
                    "source",
                    "public_id",
                    "created_at",
                    "updated_at",
                    "confirmed_at",
                    "cancelled_at",
                )
            },
        ),
    )

    @admin.display(description="Связь")
    def contact(self, obj):
        return format_html(
            '<a href="tel:{}">{}</a><br><a href="mailto:{}">{}</a>',
            obj.phone_normalized,
            obj.phone,
            obj.email,
            obj.email,
        )


@admin.action(description="Подтвердить перенос")
def approve_reschedule_action(modeladmin, request, queryset):
    for item in queryset:
        try:
            approve_reschedule_request(item)
        except ValidationError as error:
            modeladmin.message_user(request, error.messages[0], messages.WARNING)


@admin.action(description="Отклонить перенос")
def reject_reschedule_action(modeladmin, request, queryset):
    for item in queryset:
        try:
            reject_reschedule_request(item, admin_note="Отклонено администратором")
        except ValidationError as error:
            modeladmin.message_user(request, error.messages[0], messages.WARNING)


@admin.register(RescheduleRequest)
class RescheduleRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "customer",
        "old_starts_at",
        "requested_starts_at",
        "status",
        "created_at",
        "processed_at",
    )
    list_filter = ("status", "created_at", "processed_at")
    search_fields = ("booking__name", "customer__email", "booking__public_id")
    readonly_fields = (
        "booking",
        "customer",
        "requested_starts_at",
        "created_at",
        "processed_at",
    )
    actions = (approve_reschedule_action, reject_reschedule_action)

    @admin.display(description="Текущее время")
    def old_starts_at(self, obj):
        return obj.booking.starts_at


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "price_from",
        "price_to",
        "duration_minutes",
        "buffer_before",
        "buffer_after",
        "is_active",
        "is_featured",
        "order",
    )
    list_editable = ("is_active", "is_featured", "order")
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ("category", "is_active", "is_featured")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "specialization", "online_booking", "is_active", "order")
    list_editable = ("online_booking", "is_active", "order")
    filter_horizontal = ("services",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ScheduleInline, SpecialDayInline)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("type", "channel", "recipient", "status", "booking", "created_at")
    list_filter = ("type", "channel", "status", "created_at")
    search_fields = ("recipient", "text", "error")
    readonly_fields = (
        "booking",
        "type",
        "channel",
        "recipient",
        "text",
        "status",
        "error",
        "created_at",
        "sent_at",
        "dedupe_key",
    )


@admin.register(LoginToken)
class LoginTokenAdmin(admin.ModelAdmin):
    list_display = ("customer", "created_at", "expires_at", "attempts", "used_at")
    list_filter = ("created_at", "used_at")
    readonly_fields = (
        "customer",
        "token_hash",
        "code_hash",
        "expires_at",
        "attempts",
        "used_at",
        "created_at",
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("name", "rating", "service", "master", "is_published", "date")
    list_filter = ("rating", "is_published", "service", "master")
    list_editable = ("is_published",)


for model in (
    MasterTimeOff,
    Customer,
    GalleryItem,
    FAQ,
    Article,
    SiteText,
    SiteAsset,
):
    admin.site.register(model)

admin.site.site_header = "Élan Atelier — управление демо-салоном"
admin.site.index_title = "Записи, расписание и контент"
