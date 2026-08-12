# Élan Atelier — демонстрационная платформа онлайн-записи

Portfolio-grade Django-проект в фирменном стиле Élan Atelier. Это демонстрация коммерческого продукта, а не сайт действующего салона.

## Возможности

- путь записи: услуга → подходящий мастер → дата → свободный слот → контакты → подтверждение;
- расписания, перерывы, выходные, блокировки и особые рабочие дни;
- длительность и буферы услуг, защита от пересечений внутри транзакции;
- JSON API свободных слотов и мастеров;
- страница успеха и экспорт `.ics`;
- кабинет по magic-link или одноразовому коду;
- будущие записи, история, отмена, перенос и повторная запись;
- email через console backend и журнал уведомлений;
- идемпотентные напоминания командой `send_booking_reminders`;
- услуги, мастера, статьи, FAQ, галерея, отзывы и весь текст сайта в Django Admin;
- SQLite для локальной демонстрации и PostgreSQL через окружение; транзакционная блокировка строки мастера применяется при создании записи;
- sitemap, robots, noindex служебных страниц;
- адаптивный интерфейс без Bootstrap.

## Основные модели

`Service`, `TeamMember`, `MasterSchedule`, `MasterTimeOff`, `SpecialWorkingDay`, `Customer`, `Booking`, `LoginToken`, `NotificationLog`, `GalleryItem`, `Review`, `Article`, `FAQ`, `SiteText`, `SiteAsset`.

## Запуск — Windows PowerShell

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --clear
python manage.py createsuperuser
python manage.py runserver
```

Сайт: `http://127.0.0.1:8000/`  
Админка: `http://127.0.0.1:8000/admin/`

Повторный `python manage.py seed_demo` обновляет демо-набор без дублей. Будущие записи рассчитываются относительно текущей даты.

## Письма и вход

По умолчанию используется `django.core.mail.backends.console.EmailBackend`: код и magic-link печатаются в терминал. Реальный SMTP не обязателен. Срок кода — 15 минут, максимум 5 попыток.

## Команды

```powershell
python manage.py seed_demo
python manage.py seed_demo --clear
python manage.py send_booking_reminders
python manage.py test
python manage.py collectstatic --noinput
```

## Переменные окружения

Смотрите `.env.example`: секрет Django, DEBUG, hosts, PostgreSQL, email backend и необязательные Telegram-переменные. В production запуск с дефолтным `SECRET_KEY` запрещён.

## Docker

```bash
docker build -t elan-atelier .
docker run --env-file .env -p 8000:8000 elan-atelier
```

## Production checklist

1. Установить сильный `DJANGO_SECRET_KEY`, выключить DEBUG.
2. Подключить PostgreSQL и постоянное хранилище media/S3.
3. Настроить HTTPS, SMTP при необходимости и резервное копирование.
4. Выполнить `migrate`, `collectstatic`, создать администратора.
5. Запускать `send_booking_reminders` по cron.

Telegram необязателен: при наличии `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` используется Bot API с таймаутом и журналированием. Без этих переменных email и запись продолжают работать.


## Финальный аудит

Фактические результаты автоматических проверок находятся в `AUDIT_REPORT.md`. Команды, которые требуют локально установленных Django, Black, Ruff, Docker или PostgreSQL, перечислены в `MANUAL_STEPS.md`.

Онлайн-wizard требует JavaScript для загрузки проверенных свободных слотов. При отключённом JavaScript интерфейс показывает телефон и email для альтернативной связи и не заявляет о поддержке серверного wizard.

Перед публикацией используйте `PORTFOLIO_CHECKLIST.md`.

## Модель доступа v6

Страница успеха и `.ics` не являются публичными capability links: оба endpoint требуют session владельца (`customer_id`). UUID скрывает идентификатор, но не заменяет авторизацию. После входа через одноразовый magic-link или код session key меняется.

## Business value и архитектура

Проект демонстрирует полный путь онлайн-записи для портфолио студии: снижение ручной работы администратора, подбор доступного мастера, проверку расписания и буферов, self-service кабинет, перенос/отмену и журнал уведомлений. Django views отвечают за HTTP и доступ, forms — за входные данные, services — за транзакционные бизнес-операции, models — за инварианты и snapshots цены/длительности.

Фактические результаты текущей среды находятся в `AUDIT_REPORT.md`; внешние проверки — в `MANUAL_STEPS.md`. JavaScript обязателен для интерактивного выбора серверно проверенного слота.


## Финальная визуальная полировка

После browser audit wizard переведён в компактный вертикальный flow: заголовок, progress и активная карточка находятся рядом, review занимает полную ширину, длинные значения переносятся, а mobile layout не создаёт horizontal scroll. Проверены реальные сценарии записи к конкретному и любому подходящему мастеру. Безопасный доступ к success/ICS, SEO/JSON-LD и остальные фактические результаты описаны в `AUDIT_REPORT.md`.
