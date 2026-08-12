import json
from datetime import UTC, date, datetime, timedelta

from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from .forms import (
    BookingForm,
    CancelBookingForm,
    LoginCodeForm,
    LoginRequestForm,
    RescheduleForm,
)
from .models import (
    FAQ,
    Article,
    Booking,
    Customer,
    GalleryItem,
    Review,
    Service,
    TeamMember,
)
from .services.authentication import (
    consume_login_code,
    consume_magic_token,
    create_login_token,
    customer_required,
)
from .services.availability import (
    get_available_slots,
    nearest_available_dates,
    suitable_masters,
)
from .services.bookings import (
    cancel_booking as cancel_booking_service,
)
from .services.bookings import (
    create_booking,
    create_reschedule_request,
)
from .services.notifications import send_notification


def limited(request, key, limit=8, seconds=300):
    ident = request.META.get("REMOTE_ADDR", "local")
    k = f"rl:{key}:{ident}"
    value = cache.get(k, 0)
    if value >= limit:
        return True
    cache.set(k, value + 1, seconds)
    return False


def common_context():
    return {"services": Service.objects.filter(is_active=True)}


def absolute_url(request, value):
    return request.build_absolute_uri(value or "/static/studio/img/og-cover.png")


def json_ld(data):
    """Serialize structured data safely for an application/ld+json script."""
    return (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003C")
        .replace(">", "\\u003E")
        .replace("&", "\\u0026")
    )


def home(request):
    reviews = Review.objects.filter(is_published=True)
    average = reviews.aggregate(avg=Avg("rating"))["avg"]
    context = common_context() | {
        "featured_services": Service.objects.filter(is_active=True, is_featured=True)[
            :4
        ],
        "team": TeamMember.objects.filter(is_active=True)[:3],
        "master_count": TeamMember.objects.filter(is_active=True).count(),
        "gallery": GalleryItem.objects.filter(is_published=True)[:6],
        "reviews": reviews[:4],
        "rating": round(average, 1) if average is not None else None,
        "review_count": reviews.count(),
    }
    context["structured_data"] = json_ld(
        {
            "@context": "https://schema.org",
            "@type": "BeautySalon",
            "name": "Élan Atelier",
            "url": request.build_absolute_uri(reverse("studio:home")),
            "telephone": "+38 (000) 000 00 00",
            "email": "hello@elan-atelier.com",
            "image": request.build_absolute_uri("/static/studio/img/og-cover.png"),
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "Демонстрационный адрес",
                "addressLocality": "Киев",
                "addressCountry": "UA",
            },
            "openingHours": "Mo-Su 09:00-21:00",
            "description": "Демонстрационный проект салона красоты Élan Atelier.",
        }
    )
    return render(request, "studio/pages/home.html", context)


def services(request):
    faqs = FAQ.objects.filter(is_active=True, service__isnull=True)
    structured_data = json_ld(
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq.question,
                    "acceptedAnswer": {"@type": "Answer", "text": faq.answer},
                }
                for faq in faqs
                if faq.question and faq.answer
            ],
        }
    )
    return render(
        request,
        "studio/pages/services.html",
        common_context() | {"faqs": faqs, "structured_data": structured_data},
    )


def service_detail(request, slug):
    obj = get_object_or_404(Service, slug=slug, is_active=True)
    return render(
        request,
        "studio/pages/service_detail.html",
        common_context()
        | {
            "item": obj,
            "masters": suitable_masters(obj),
            "works": obj.gallery_items.filter(is_published=True),
            "faqs": FAQ.objects.filter(is_active=True).filter(
                Q(service=obj) | Q(service__isnull=True)
            ),
            "page_og_image": absolute_url(request, obj.image_url),
            "structured_data": json_ld(
                {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": 1,
                            "name": "Услуги",
                            "item": request.build_absolute_uri(
                                reverse("studio:services")
                            ),
                        },
                        {
                            "@type": "ListItem",
                            "position": 2,
                            "name": obj.title,
                            "item": request.build_absolute_uri(),
                        },
                    ],
                }
            ),
        },
    )


def about(request):
    return render(request, "studio/pages/about.html", common_context())


def team(request):
    return render(
        request,
        "studio/pages/team.html",
        common_context() | {"members": TeamMember.objects.filter(is_active=True)},
    )


def team_detail(request, slug):
    obj = get_object_or_404(TeamMember, slug=slug, is_active=True)
    return render(
        request,
        "studio/pages/team_detail.html",
        common_context()
        | {
            "item": obj,
            "works": obj.gallery_items.filter(is_published=True),
            "reviews": obj.reviews.filter(is_published=True),
            "page_og_image": absolute_url(request, obj.image_url),
            "structured_data": json_ld(
                {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": 1,
                            "name": "Команда",
                            "item": request.build_absolute_uri(reverse("studio:team")),
                        },
                        {
                            "@type": "ListItem",
                            "position": 2,
                            "name": obj.name,
                            "item": request.build_absolute_uri(),
                        },
                    ],
                }
            ),
        },
    )


def gallery(request):
    items = GalleryItem.objects.filter(is_published=True)
    category = request.GET.get("category")
    if category:
        items = items.filter(category=category)
    return render(
        request,
        "studio/pages/gallery.html",
        common_context()
        | {
            "items": items,
            "categories": GalleryItem.objects.filter(is_published=True)
            .values_list("category", flat=True)
            .distinct(),
            "selected": category,
        },
    )


def journal(request):
    queryset = Article.objects.filter(is_published=True)
    page_obj = Paginator(queryset, 6).get_page(request.GET.get("page"))
    return render(
        request,
        "studio/pages/journal.html",
        common_context() | {"articles": page_obj.object_list, "page_obj": page_obj},
    )


def article(request, slug):
    item = get_object_or_404(Article, slug=slug, is_published=True)
    related = Article.objects.filter(is_published=True, category=item.category).exclude(
        pk=item.pk
    )[:3]
    structured_data = json_ld(
        [
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": item.title,
                "description": item.excerpt,
                "image": absolute_url(request, item.image_url),
                "datePublished": item.published_at.isoformat(),
                "dateModified": item.updated_at.date().isoformat(),
                "author": {"@type": "Organization", "name": "Редакция Élan Atelier"},
                "mainEntityOfPage": request.build_absolute_uri(),
            },
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Журнал",
                        "item": request.build_absolute_uri(reverse("studio:journal")),
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": item.title,
                        "item": request.build_absolute_uri(),
                    },
                ],
            },
        ]
    )
    return render(
        request,
        "studio/pages/article.html",
        common_context()
        | {
            "article": item,
            "related": related,
            "page_og_image": absolute_url(request, item.image_url),
            "structured_data": structured_data,
        },
    )


def contacts(request):
    return render(request, "studio/pages/contacts.html", common_context())


def privacy(request):
    return render(request, "studio/pages/privacy.html", common_context())


def available_masters(request):
    raw = request.GET.get("service", "")
    service = (
        Service.objects.filter(pk=int(raw), is_active=True).first()
        if str(raw).isdigit()
        else Service.objects.filter(slug=raw, is_active=True).first()
    )
    if not service:
        return JsonResponse({"error": "Услуга не найдена"}, status=400)
    return JsonResponse(
        {
            "service": {
                "category": service.category,
                "price": service.price_display,
                "duration": service.duration_minutes,
            },
            "masters": [
                {
                    "id": m.pk,
                    "name": m.name,
                    "specialization": m.specialization,
                    "experience": m.experience,
                    "image": m.image_url,
                }
                for m in suitable_masters(service)
            ],
        }
    )


def available_slots(request):
    slug = request.GET.get("service")
    raw_date = request.GET.get("date")
    master_raw = request.GET.get("master", "")
    service = (
        Service.objects.filter(pk=int(slug), is_active=True).first()
        if str(slug).isdigit()
        else Service.objects.filter(slug=slug, is_active=True).first()
    )
    if not service:
        return JsonResponse({"error": "Услуга не найдена или недоступна"}, status=400)
    try:
        day = date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Передайте дату в формате YYYY-MM-DD"}, status=400
        )
    today = timezone.localdate()
    if not today <= day <= today + timedelta(days=60):
        return JsonResponse({"error": "Выберите дату в пределах 60 дней"}, status=400)
    master = None
    if master_raw and master_raw not in ("any", "0"):
        if not str(master_raw).isdigit():
            return JsonResponse(
                {"error": "Некорректный идентификатор мастера"}, status=400
            )
        master = TeamMember.objects.filter(
            pk=int(master_raw), is_active=True, online_booking=True
        ).first()
        if not master or not master.services.filter(pk=service.pk).exists():
            return JsonResponse(
                {"error": "Мастер не выполняет выбранную услугу"}, status=400
            )
    slots = get_available_slots(service, master, day)
    return JsonResponse(
        {
            "date": day.isoformat(),
            "slots": [
                {
                    k: v
                    for k, v in slot.items()
                    if k in ("time", "master_id", "master_name")
                }
                for slot in slots
            ],
            "nearest_dates": (
                [] if slots else nearest_available_dates(service, master, day)
            ),
        }
    )


def booking_error_step(form):
    if not form.is_bound:
        return 1
    fields = set(form.errors)
    if "service" in fields:
        return 1
    if "master" in fields:
        return 2
    if "date" in fields:
        return 3
    if fields & {"time", "selected_master"}:
        return 4
    return 5


def booking(request):
    initial = {
        "service": Service.objects.filter(
            slug=request.GET.get("service"), is_active=True
        ).first(),
        "master": TeamMember.objects.filter(
            slug=request.GET.get("master"), is_active=True
        ).first(),
    }
    form = BookingForm(request.POST or None, initial=initial)
    if request.method == "POST":
        if limited(request, "booking", 12, 600):
            form.add_error(None, "Слишком много попыток. Подождите несколько минут.")
        elif form.is_valid():
            service = form.cleaned_data["service"]
            master = form.cleaned_data.get("master")
            selected_id = form.cleaned_data.get("selected_master")
            if master and selected_id and (master.pk != selected_id):
                form.add_error("master", "Выбранный мастер не совпадает со слотом.")
            elif not (master or selected_id):
                form.add_error("master", "Выберите мастера и свободное время.")
            else:
                master_id = master.pk if master else selected_id
                starts_at = timezone.make_aware(
                    datetime.combine(
                        form.cleaned_data["date"], form.cleaned_data["time"]
                    ),
                    timezone.get_current_timezone(),
                )
                customer, _ = Customer.objects.update_or_create(
                    email=form.cleaned_data["email"].lower(),
                    defaults={
                        "name": form.cleaned_data["name"],
                        "phone_normalized": form.cleaned_data["phone"],
                        "consent": True,
                        "consent_at": timezone.now(),
                    },
                )
                try:
                    item = create_booking(
                        service_id=service.pk,
                        master_id=master_id,
                        starts_at=starts_at,
                        customer=customer,
                        message=form.cleaned_data["message"],
                    )
                except (
                    ValidationError,
                    TeamMember.DoesNotExist,
                    Service.DoesNotExist,
                ) as error:
                    form.add_error(
                        "time",
                        error.messages[0] if hasattr(error, "messages") else str(error),
                    )
                else:
                    credentials = create_login_token(customer)
                    magic_url = request.build_absolute_uri(
                        reverse("studio:magic_login", args=[credentials.raw_token])
                    )
                    calendar_url = request.build_absolute_uri(
                        reverse("studio:booking_ics", args=[item.public_id])
                    )
                    local_start = timezone.localtime(item.starts_at)
                    email_text = (
                        f"Заявка #{item.pk} создана.\n"
                        f"Услуга: {item.service.title}\n"
                        f"Мастер: {item.master.name}\n"
                        f"Дата и время: {local_start:%d.%m.%Y %H:%M}\n"
                        f"Длительность: {item.duration_minutes} минут\n"
                        f"Цена: {item.price} ₴\n"
                        f"Вход в кабинет: {magic_url}\n"
                        "Чтобы скачать календарь на этом или другом устройстве:\n"
                        f"1. Сначала откройте ссылку входа: {magic_url}\n"
                        "2. Откройте запись в кабинете.\n"
                        f"3. Добавить в календарь: {calendar_url}\n"
                        "Прямая ссылка календаря требует активного входа.\n"
                        "Отмена и перенос доступны не позднее чем за 12 часов до визита."
                    )

                    send_notification(
                        kind="booking_created",
                        recipient=customer.email,
                        text=email_text,
                        booking=item,
                        dedupe_key=f"created:{item.pk}",
                        notify_admin=True,
                    )
                    request.session.cycle_key()
                    request.session["customer_id"] = customer.pk
                    return redirect("studio:booking_success", public_id=item.public_id)
    return render(
        request,
        "studio/pages/booking.html",
        common_context() | {"form": form, "initial_step": booking_error_step(form)},
    )


def _owned_booking(request, public_id):
    customer_id = request.session.get("customer_id")
    if not customer_id:
        raise Http404
    return get_object_or_404(
        Booking, public_id=public_id, customer_id=customer_id, customer__isnull=False
    )


def booking_success(request, public_id):
    item = _owned_booking(request, public_id)
    return render(
        request, "studio/pages/booking_success.html", common_context() | {"item": item}
    )


def _ics_escape(value):
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def booking_ics(request, public_id):
    booking = _owned_booking(request, public_id)
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    starts_at = booking.starts_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    ends_at = booking.ends_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    local_start = timezone.localtime(booking.starts_at)
    description = f"Услуга: {booking.service.title}\nМастер: {booking.master.name}\nДата и время: {local_start:%d.%m.%Y %H:%M}\nНомер записи: {booking.pk}"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Élan Atelier Demo//Booking//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{booking.public_id}@elan.demo",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{starts_at}",
        f"DTEND:{ends_at}",
        f"SUMMARY:{_ics_escape(f'Élan Atelier — {booking.service.title}')}",
        f"DESCRIPTION:{_ics_escape(description)}",
        f"LOCATION:{_ics_escape('Демонстрационный адрес · центр Киева')}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    response = HttpResponse(
        "\r\n".join(lines), content_type="text/calendar; charset=utf-8"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="elan-{booking.public_id}.ics"'
    )
    return response


def login_request(request):
    form = LoginRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if limited(request, "login", 5, 600):
            form.add_error(None, "Слишком много попыток. Попробуйте позже.")
        else:
            email = form.cleaned_data["email"].lower()
            customer = Customer.objects.filter(email__iexact=email).first()
            if customer:
                credentials = create_login_token(customer)
                link = request.build_absolute_uri(
                    reverse("studio:magic_login", args=[credentials.raw_token])
                )
                send_notification(
                    kind="login",
                    recipient=email,
                    text=f"Код входа: {credentials.code}\nСсылка: {link}",
                    dedupe_key=f"login:{credentials.record.pk}",
                )
            request.session["login_email"] = email
            messages.success(request, "Если email найден, код и ссылка отправлены.")
            return redirect("studio:login_code")
    return render(request, "studio/pages/login.html", common_context() | {"form": form})


def login_code(request):
    form = LoginCodeForm(
        request.POST or None, initial={"email": request.session.get("login_email", "")}
    )
    if request.method == "POST" and form.is_valid():
        customer = consume_login_code(
            form.cleaned_data["email"], form.cleaned_data["code"]
        )
        if customer:
            request.session.cycle_key()
            request.session["customer_id"] = customer.pk
            return redirect("studio:cabinet")
        form.add_error("code", "Неверный или просроченный код.")
    return render(
        request, "studio/pages/login_code.html", common_context() | {"form": form}
    )


def magic_login(request, token):
    customer = consume_magic_token(token)
    if not customer:
        return render(
            request, "studio/pages/login_expired.html", common_context(), status=400
        )
    request.session.cycle_key()
    request.session["customer_id"] = customer.pk
    return redirect("studio:cabinet")


def logout_customer(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    request.session.flush()
    return redirect("studio:home")


@customer_required
def cabinet(request):
    customer = request.customer
    now = timezone.now()
    return render(
        request,
        "studio/pages/cabinet.html",
        common_context()
        | {
            "customer": customer,
            "upcoming": customer.bookings.filter(starts_at__gte=now).exclude(
                status__startswith="cancelled"
            ),
            "history": customer.bookings.filter(
                Q(starts_at__lt=now) | Q(status__startswith="cancelled")
            ),
        },
    )


@customer_required
def booking_detail(request, public_id):
    item = get_object_or_404(Booking, public_id=public_id, customer=request.customer)
    return render(
        request,
        "studio/pages/booking_detail.html",
        common_context()
        | {
            "item": item,
            "cancel_form": CancelBookingForm(),
            "reschedule_form": RescheduleForm(),
            "reschedule": item.reschedule_requests.first(),
        },
    )


@customer_required
def cancel_booking(request, public_id):
    item = get_object_or_404(Booking, public_id=public_id, customer=request.customer)
    if request.method != "POST":
        return HttpResponse(status=405)
    form = CancelBookingForm(request.POST)
    if form.is_valid():
        try:
            cancel_booking_service(
                item, reason=form.cleaned_data["reason"], by_client=True
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, "Запись отменена.")
    return redirect("studio:booking_detail", public_id=item.public_id)


@customer_required
def reschedule_slots(request, public_id):
    item = get_object_or_404(Booking, public_id=public_id, customer=request.customer)
    try:
        day = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return JsonResponse(
            {"error": "Передайте дату в формате YYYY-MM-DD"}, status=400
        )
    today = timezone.localdate()
    if not today <= day <= today + timedelta(days=60):
        return JsonResponse({"error": "Выберите дату в пределах 60 дней"}, status=400)
    if not item.can_reschedule:
        return JsonResponse({"error": "Перенос для этой записи недоступен"}, status=400)
    slots = get_available_slots(
        item.service, item.master, day, exclude_booking_id=item.pk
    )
    nearest = []
    if not slots:
        for offset in range(1, 61):
            candidate = day + timedelta(days=offset)
            if get_available_slots(
                item.service, item.master, candidate, exclude_booking_id=item.pk
            ):
                nearest.append(candidate.isoformat())
                if len(nearest) == 3:
                    break
    return JsonResponse(
        {
            "date": day.isoformat(),
            "slots": [
                {
                    k: v
                    for k, v in slot.items()
                    if k in ("time", "master_id", "master_name")
                }
                for slot in slots
            ],
            "nearest_dates": nearest,
        }
    )


@customer_required
def request_reschedule(request, public_id):
    item = get_object_or_404(Booking, public_id=public_id, customer=request.customer)
    if request.method != "POST":
        return HttpResponse(status=405)
    form = RescheduleForm(request.POST)
    if form.is_valid():
        starts_at = timezone.make_aware(
            datetime.combine(form.cleaned_data["date"], form.cleaned_data["time"]),
            timezone.get_current_timezone(),
        )
        try:
            create_reschedule_request(
                item, request.customer, starts_at, form.cleaned_data["comment"]
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, "Запрос на перенос отправлен")
    else:
        return render(
            request,
            "studio/pages/booking_detail.html",
            common_context()
            | {
                "item": item,
                "cancel_form": CancelBookingForm(),
                "reschedule_form": form,
                "reschedule": item.reschedule_requests.first(),
                "open_reschedule": True,
            },
            status=400,
        )
    return redirect("studio:booking_detail", public_id=item.public_id)


def robots(request):
    return HttpResponse(
        "User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /cabinet/\nDisallow: /booking/success/\nDisallow: /api/\nSitemap: "
        + request.build_absolute_uri("/sitemap.xml")
        + "\n",
        content_type="text/plain",
    )


def sitemap(request):
    urls = [
        (reverse("studio:" + n), None)
        for n in ["home", "services", "about", "team", "journal", "gallery", "contacts"]
    ]
    urls += [
        (reverse("studio:service_detail", args=[x.slug]), x.updated_at)
        for x in Service.objects.filter(is_active=True)
    ]
    urls += [
        (reverse("studio:team_detail", args=[x.slug]), x.updated_at)
        for x in TeamMember.objects.filter(is_active=True)
    ]
    urls += [
        (reverse("studio:article", args=[x.slug]), x.updated_at)
        for x in Article.objects.filter(is_published=True)
    ]
    body = "".join(
        (
            f"<url><loc>{escape(request.build_absolute_uri(url))}</loc>{(f'<lastmod>{changed.date().isoformat()}</lastmod>' if changed else '')}</url>"
            for url, changed in urls
        )
    )
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + body
        + "</urlset>",
        content_type="application/xml; charset=utf-8",
    )


def custom_404(request, exception):
    return render(request, "studio/pages/404.html", status=404)


def custom_500(request):
    return render(request, "studio/pages/500.html", status=500)
