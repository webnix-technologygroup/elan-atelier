import uuid
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from studio.demo_data import ARTICLES, ASSETS, TEXTS
from studio.models import (
    FAQ,
    Article,
    Booking,
    Customer,
    GalleryItem,
    LoginToken,
    MasterSchedule,
    MasterTimeOff,
    NotificationLog,
    Review,
    Service,
    SiteAsset,
    SiteText,
    SpecialWorkingDay,
    TeamMember,
)


class Command(BaseCommand):
    help = "Идемпотентно создаёт демонстрационные данные Élan Atelier"

    def add_arguments(self, p):
        p.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **o):
        if o["clear"]:
            NotificationLog.objects.all().delete()
            Booking.objects.all().delete()
            LoginToken.objects.all().delete()
            Customer.objects.all().delete()
            Review.objects.all().delete()
            GalleryItem.objects.all().delete()
            MasterTimeOff.objects.all().delete()
            SpecialWorkingDay.objects.all().delete()
            MasterSchedule.objects.all().delete()
            TeamMember.objects.all().delete()
            Service.objects.all().delete()
            FAQ.objects.all().delete()
            Article.objects.all().delete()
            SiteAsset.objects.all().delete()
            SiteText.objects.all().delete()
        for n, (section, key, label, value) in enumerate(TEXTS, 1):
            SiteText.objects.update_or_create(
                key=key,
                defaults={
                    "section": section,
                    "label": label,
                    "value": value,
                    "order": n,
                },
            )
        for n, (section, key, label, path) in enumerate(ASSETS, 1):
            SiteAsset.objects.update_or_create(
                key=key,
                defaults={
                    "section": section,
                    "label": label,
                    "fallback_path": path,
                    "order": n,
                },
            )
        specs = [
            (
                "haircut",
                "Стрижка & форма",
                "Стрижки",
                "Архитектура формы для вашего ритма.",
                1800,
                2600,
                90,
                "scissors",
                "look-1.svg",
            ),
            (
                "color",
                "Цвет & свет",
                "Окрашивание",
                "Мягкие переходы и сложные оттенки.",
                3200,
                7200,
                180,
                "color",
                "look-2.svg",
            ),
            (
                "care",
                "Уход & восстановление",
                "Уход",
                "Персональный протокол блеска и плотности.",
                1400,
                2600,
                60,
                "sparkle",
                "atelier.svg",
            ),
            (
                "event",
                "Образ & событие",
                "Образ",
                "Укладка и макияж без ощущения маски.",
                2400,
                4200,
                120,
                "brush",
                "hero.svg",
            ),
            (
                "bangs",
                "Чёлка & контур",
                "Стрижки",
                "Точная быстрая коррекция формы.",
                700,
                1100,
                30,
                "scissors",
                "details.svg",
            ),
            (
                "consultation",
                "Консультация",
                "Диагностика",
                "Диагностика и персональный план.",
                500,
                500,
                45,
                "sparkle",
                "atelier.svg",
            ),
        ]
        services = {}
        for i, (slug, title, cat, desc, p1, p2, dur, icon, img) in enumerate(specs, 1):
            services[slug], _ = Service.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "category": cat,
                    "eyebrow": "Услуга",
                    "short_description": desc,
                    "description": desc
                    + " Мастер уточнит детали и подтвердит итоговую стоимость до начала работы.",
                    "price_from": p1,
                    "price_to": p2,
                    "duration_minutes": dur,
                    "buffer_before": 0,
                    "buffer_after": 15,
                    "icon": icon,
                    "fallback_image": img,
                    "order": i,
                    "is_active": True,
                    "is_featured": i <= 4,
                },
            )
        masters_data = [
            (
                "maria-levchenko",
                "Мария Левченко",
                "Арт-директор",
                "Стрижки и форма",
                "12 лет практики",
                "look-1.svg",
                ["haircut", "bangs", "consultation"],
            ),
            (
                "olga-romaniuk",
                "Ольга Романюк",
                "Колорист",
                "Сложное окрашивание",
                "9 лет практики",
                "look-2.svg",
                ["color", "care", "consultation"],
            ),
            (
                "irina-savchuk",
                "Ирина Савчук",
                "Стилист",
                "Текстура и уход",
                "7 лет практики",
                "atelier.svg",
                ["haircut", "care", "event", "consultation"],
            ),
            (
                "lera-koval",
                "Лера Коваль",
                "Визажист",
                "Образы и события",
                "6 лет практики",
                "hero.svg",
                ["event", "consultation"],
            ),
        ]
        masters = []
        for i, (slug, name, role, special, exp, img, skills) in enumerate(
            masters_data, 1
        ):
            m, _ = TeamMember.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "role": role,
                    "specialization": special,
                    "bio": f"{special}, бережная работа и точная консультация.",
                    "bio_full": f"{name} работает с индивидуальной формой и объясняет каждый этап. Рекомендации подбираются под конкретного клиента.",
                    "experience": exp,
                    "image": img,
                    "order": i,
                    "is_active": True,
                    "online_booking": True,
                },
            )
            m.services.set([services[x] for x in skills])
            masters.append(m)
            for wd in range(6):
                MasterSchedule.objects.update_or_create(
                    master=m,
                    weekday=wd,
                    defaults={
                        "start_time": time(9),
                        "end_time": time(19),
                        "break_start": time(13),
                        "break_end": time(14),
                        "is_active": True,
                    },
                )
        block_day = timezone.localdate() + timedelta(days=14)
        MasterTimeOff.objects.update_or_create(
            master=masters[0],
            starts_at=timezone.make_aware(
                __import__("datetime").datetime.combine(block_day, time.min)
            ),
            defaults={
                "ends_at": timezone.make_aware(
                    __import__("datetime").datetime.combine(block_day, time.max)
                ),
                "reason": "Демонстрационный выходной",
                "all_day": True,
            },
        )
        for i, (q, a) in enumerate(
            [
                (
                    "Как узнать точную стоимость?",
                    "Мастер подтвердит стоимость после диагностики до начала работы.",
                ),
                (
                    "Можно прийти только на консультацию?",
                    "Да, выберите услугу «Консультация».",
                ),
                (
                    "Что делать при опоздании?",
                    "Свяжитесь с администратором — мы проверим расписание.",
                ),
            ],
            1,
        ):
            FAQ.objects.update_or_create(
                question=q, defaults={"answer": a, "order": i, "is_active": True}
            )
        for data in ARTICLES:
            data = data.copy()
            slug = data.pop("slug")
            Article.objects.update_or_create(slug=slug, defaults=data)
        fallback = [
            "look-1.svg",
            "look-2.svg",
            "atelier.svg",
            "hero.svg",
            "details.svg",
            "look-1.svg",
        ]
        for i, s in enumerate(services.values()):
            GalleryItem.objects.update_or_create(
                title=f"Работа · {s.title}",
                defaults={
                    "category": s.category,
                    "service": s,
                    "master": masters[i % 4],
                    "fallback_image": fallback[i],
                    "alt": f"Демонстрационная работа: {s.title}",
                    "description": "Пример результата для портфолио интерфейса.",
                    "is_published": True,
                    "order": i,
                },
            )
        for i, (name, rating, text) in enumerate(
            [
                ("Анна", 5, "Очень спокойный сервис и понятная консультация."),
                ("Марина", 5, "Форма легко укладывается дома."),
                ("Елена", 4, "Понравился точный план ухода."),
                ("София", 5, "Красивый цвет и бережная работа."),
            ],
            1,
        ):
            Review.objects.update_or_create(
                name=name,
                text=text,
                defaults={
                    "rating": rating,
                    "service": list(services.values())[i % 6],
                    "master": masters[i % 4],
                    "date": timezone.localdate() - timedelta(days=i * 8),
                    "source": "Демонстрационный отзыв",
                    "is_published": True,
                    "order": i,
                },
            )
        customers = []
        for i in range(3):
            customers.append(
                Customer.objects.update_or_create(
                    email=f"demo{i + 1}@example.test",
                    defaults={
                        "name": f"Демо-клиент {i + 1}",
                        "phone_normalized": f"+3800000000{i}",
                        "consent": True,
                        "consent_at": timezone.now(),
                    },
                )[0]
            )
        statuses = ["pending", "confirmed", "completed", "cancelled_by_client"]
        for i, status in enumerate(statuses):
            start = timezone.now() + timedelta(days=i + 1 if i < 2 else -i - 1)
            start = start.replace(hour=10 + i, minute=0, second=0, microsecond=0)
            service = list(services.values())[i]
            public = uuid.uuid5(uuid.NAMESPACE_DNS, f"elan-demo-{i}")
            Booking.objects.update_or_create(
                public_id=public,
                defaults={
                    "customer": customers[i % 3],
                    "name": customers[i % 3].name,
                    "phone": customers[i % 3].phone_normalized,
                    "phone_normalized": customers[i % 3].phone_normalized,
                    "email": customers[i % 3].email,
                    "service": service,
                    "master": masters[i % 4],
                    "preferred_date": start.date(),
                    "starts_at": start,
                    "ends_at": start + timedelta(minutes=service.duration_minutes),
                    "duration_minutes": service.duration_minutes,
                    "buffer_before_minutes": service.buffer_before,
                    "buffer_after_minutes": service.buffer_after,
                    "price": service.price_from,
                    "source": "demo",
                    "status": status,
                    "cancelled_at": (
                        timezone.now() if status.startswith("cancelled") else None
                    ),
                },
            )
        self.stdout.write(self.style.SUCCESS("Демо-данные онлайн-записи готовы"))
