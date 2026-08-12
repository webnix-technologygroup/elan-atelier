import uuid
from datetime import timedelta

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

CONTENT_SECTIONS = [
    ("global", "Общие настройки"),
    ("home", "Главная"),
    ("services", "Услуги"),
    ("about", "О нас"),
    ("team", "Команда"),
    ("journal", "Журнал"),
    ("contacts", "Контакты"),
    ("booking", "Запись"),
    ("cabinet", "Личный кабинет"),
    ("privacy", "Конфиденциальность"),
    ("errors", "Ошибки"),
]


def validate_image_size(value):
    if not value:
        return
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Максимальный размер изображения — 5 МБ.")
    try:
        image = Image.open(value)
        image.verify()
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValidationError("Допустимы только JPEG, PNG и WebP.")
        value.seek(0)
        image = Image.open(value)
        if image.width > 8000 or image.height > 8000:
            raise ValidationError(
                "Разрешение изображения не должно превышать 8000×8000."
            )
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("Файл повреждён или не является изображением.")


class SiteText(models.Model):
    section = models.CharField("Раздел", max_length=30, choices=CONTENT_SECTIONS)
    key = models.SlugField("Системный ключ", max_length=100, unique=True)
    label = models.CharField("Название поля", max_length=160)
    value = models.TextField("Текст", blank=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["section", "order", "key"]
        verbose_name = "текст сайта"
        verbose_name_plural = "Тексты сайта"

    def __str__(self):
        return f"{self.get_section_display()}: {self.label}"


class SiteAsset(models.Model):
    section = models.CharField("Раздел", max_length=30, choices=CONTENT_SECTIONS)
    key = models.SlugField("Системный ключ", max_length=100, unique=True)
    label = models.CharField("Название изображения", max_length=160)
    file = models.ImageField(
        "Изображение", upload_to="site/", blank=True, validators=[validate_image_size]
    )
    fallback_path = models.CharField(
        "Резервный static-файл", max_length=200, blank=True
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["section", "order", "key"]
        verbose_name = "изображение сайта"
        verbose_name_plural = "Изображения сайта"

    @property
    def url(self):
        return (
            self.file.url
            if self.file
            else (
                staticfiles_storage.url(self.fallback_path)
                if self.fallback_path
                else ""
            )
        )

    def __str__(self):
        return self.label


class Service(models.Model):
    slug = models.SlugField(unique=True)
    category = models.CharField("Категория", max_length=80, default="Салон")
    title = models.CharField(max_length=120)
    eyebrow = models.CharField(max_length=80, default="Услуга")
    short_description = models.CharField(
        "Короткое описание", max_length=260, blank=True
    )
    description = models.TextField("Полное описание")
    price = models.CharField(max_length=60, blank=True)
    price_from = models.PositiveIntegerField("Цена от", default=0)
    price_to = models.PositiveIntegerField("Цена до", null=True, blank=True)
    duration = models.CharField(max_length=60, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(
        "Длительность, минут", default=60
    )
    buffer_before = models.PositiveSmallIntegerField("Буфер до", default=0)
    buffer_after = models.PositiveSmallIntegerField("Буфер после", default=10)
    icon = models.CharField(max_length=40, default="sparkle")
    uploaded_icon = models.ImageField(
        upload_to="services/", blank=True, validators=[validate_image_size]
    )
    image = models.ImageField(
        upload_to="services/", blank=True, validators=[validate_image_size]
    )
    fallback_image = models.CharField(max_length=120, default="details.svg", blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField("Активна", default=True)
    is_featured = models.BooleanField("На главной", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "услуга"
        verbose_name_plural = "Услуги"

    @property
    def icon_url(self):
        return (
            self.uploaded_icon.url
            if self.uploaded_icon
            else staticfiles_storage.url(f"studio/img/icons/{self.icon}.svg")
        )

    @property
    def image_url(self):
        return (
            self.image.url
            if self.image
            else staticfiles_storage.url(f"studio/img/{self.fallback_image}")
        )

    @property
    def price_display(self):
        return (
            f"{self.price_from:,}–{self.price_to:,} ₴".replace(",", " ")
            if self.price_to and self.price_to != self.price_from
            else f"от {self.price_from:,} ₴".replace(",", " ")
        )

    def clean(self):
        errors = {}
        if self.duration_minutes <= 0:
            errors["duration_minutes"] = "Длительность должна быть больше нуля."
        if self.price_to is not None and self.price_to < self.price_from:
            errors["price_to"] = "Цена до не может быть меньше цены от."
        if self.buffer_before > 240:
            errors["buffer_before"] = "Буфер до не должен превышать 240 минут."
        if self.buffer_after > 240:
            errors["buffer_after"] = "Буфер после не должен превышать 240 минут."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title


class TeamMember(models.Model):
    slug = models.SlugField(unique=True, default="master")
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    specialization = models.CharField("Специализация", max_length=160, blank=True)
    bio = models.CharField(max_length=240)
    bio_full = models.TextField("Подробная биография", blank=True)
    experience = models.CharField(max_length=80)
    image = models.CharField(max_length=120, default="atelier.svg")
    uploaded_image = models.ImageField(
        upload_to="team/", blank=True, validators=[validate_image_size]
    )
    services = models.ManyToManyField(Service, blank=True, related_name="masters")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    online_booking = models.BooleanField("Онлайн-запись", default=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "мастер"
        verbose_name_plural = "Команда"

    @property
    def image_url(self):
        return (
            self.uploaded_image.url
            if self.uploaded_image
            else staticfiles_storage.url(f"studio/img/{self.image}")
        )

    def __str__(self):
        return self.name


class MasterSchedule(models.Model):
    WEEKDAYS = [
        (0, "Понедельник"),
        (1, "Вторник"),
        (2, "Среда"),
        (3, "Четверг"),
        (4, "Пятница"),
        (5, "Суббота"),
        (6, "Воскресенье"),
    ]
    master = models.ForeignKey(
        TeamMember, on_delete=models.CASCADE, related_name="schedules"
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("master", "weekday")
        ordering = ["master", "weekday"]
        verbose_name = "расписание"
        verbose_name_plural = "Расписание"

    def clean(self):
        errors = {}
        if self.start_time >= self.end_time:
            errors["end_time"] = "Конец смены должен быть позже начала."
        if bool(self.break_start) != bool(self.break_end):
            errors["break_start"] = "Укажите оба края перерыва."
        if self.break_start and self.break_end:
            if not self.start_time < self.break_start < self.break_end < self.end_time:
                errors["break_end"] = "Перерыв должен находиться внутри смены."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.master} — {self.get_weekday_display()}"


class MasterTimeOff(models.Model):
    master = models.ForeignKey(
        TeamMember, on_delete=models.CASCADE, related_name="time_offs"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    all_day = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_at"]
        verbose_name = "блокировка"
        verbose_name_plural = "Блокировки"

    def clean(self):
        if self.starts_at >= self.ends_at:
            raise ValidationError(
                {"ends_at": "Конец блокировки должен быть позже начала."}
            )


class SpecialWorkingDay(models.Model):
    master = models.ForeignKey(
        TeamMember, on_delete=models.CASCADE, related_name="special_days"
    )
    date = models.DateField()
    is_working = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ("master", "date")
        verbose_name = "особый день"
        verbose_name_plural = "Особые дни"

    def clean(self):
        if self.is_working and (not self.start_time or not self.end_time):
            raise ValidationError("Для рабочего дня укажите начало и конец.")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": "Конец должен быть позже начала."})
        if bool(self.break_start) != bool(self.break_end):
            raise ValidationError("Укажите оба края перерыва.")
        if self.break_start and self.break_end:
            if not self.start_time < self.break_start < self.break_end < self.end_time:
                raise ValidationError("Перерыв должен находиться внутри смены.")


class Customer(models.Model):
    name = models.CharField(max_length=120)
    phone_normalized = models.CharField(max_length=24, blank=True, db_index=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    consent = models.BooleanField(default=False)
    consent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "клиент"
        verbose_name_plural = "Клиенты"

    def __str__(self):
        return f"{self.name} · {self.email}"


class LoginToken(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="login_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def valid(self):
        return (
            not self.used_at
            and self.expires_at > timezone.now()
            and (self.attempts < 5)
        )


class Booking(models.Model):
    STATUS = [
        ("pending", "Ожидает подтверждения"),
        ("confirmed", "Подтверждена"),
        ("in_progress", "В работе"),
        ("completed", "Завершена"),
        ("cancelled_by_client", "Отменена клиентом"),
        ("cancelled_by_admin", "Отменена администратором"),
        ("no_show", "Не пришёл"),
    ]
    ACTIVE_STATUSES = ("pending", "confirmed", "in_progress")
    SOURCE = [
        ("website", "Сайт"),
        ("admin", "Администратор"),
        ("repeat", "Повторная запись"),
        ("demo", "Демо"),
    ]
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40)
    phone_normalized = models.CharField(max_length=24, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="bookings"
    )
    master = models.ForeignKey(
        TeamMember, on_delete=models.PROTECT, related_name="bookings", null=True
    )
    preferred_date = models.DateField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(default=0)
    buffer_before_minutes = models.PositiveSmallIntegerField(default=0)
    buffer_after_minutes = models.PositiveSmallIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=SOURCE, default="website")
    status = models.CharField(
        max_length=30, choices=STATUS, default="pending", db_index=True
    )
    visitor_token_hash = models.CharField(
        max_length=64, blank=True, db_index=True, editable=False
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    reschedule_requested = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_at", "-created_at"]
        verbose_name = "запись"
        verbose_name_plural = "Записи"
        indexes = [models.Index(fields=["master", "starts_at", "ends_at"])]

    def clean(self):
        errors = {}
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            errors["ends_at"] = "Конец записи должен быть позже начала."
        if (
            self.master_id
            and self.service_id
            and not self.master.services.filter(pk=self.service_id).exists()
        ):
            errors["master"] = "Мастер не выполняет выбранную услугу."
        if self.status in self.ACTIVE_STATUSES and (
            not self.master_id or not self.starts_at or not self.ends_at
        ):
            errors["starts_at"] = "Активной записи нужны мастер и точное время."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.name} — {self.service} — {self.starts_at or self.preferred_date}"

    @property
    def is_cancelled(self):
        return self.status in {"cancelled_by_client", "cancelled_by_admin"}

    @property
    def is_upcoming(self):
        return bool(self.starts_at and self.starts_at > timezone.now())

    @property
    def can_cancel(self):
        return (
            self.status in self.ACTIVE_STATUSES
            and self.is_upcoming
            and (self.starts_at > timezone.now() + timedelta(hours=12))
        )

    @property
    def can_reschedule(self):
        return self.can_cancel and (
            not self.reschedule_requests.filter(status="pending").exists()
        )

    @property
    def occupied_starts_at(self):
        return (
            self.starts_at - timedelta(minutes=self.buffer_before_minutes)
            if self.starts_at
            else None
        )

    @property
    def occupied_ends_at(self):
        return (
            self.ends_at + timedelta(minutes=self.buffer_after_minutes)
            if self.ends_at
            else None
        )


class RescheduleRequest(models.Model):
    STATUS = [
        ("pending", "Ожидает"),
        ("approved", "Подтверждён"),
        ("rejected", "Отклонён"),
        ("cancelled", "Отменён"),
    ]
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="reschedule_requests"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="reschedule_requests"
    )
    requested_starts_at = models.DateTimeField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking"],
                condition=models.Q(status="pending"),
                name="one_pending_reschedule",
            )
        ]

    def clean(self):
        errors = {}
        if (
            self.customer_id
            and self.booking_id
            and self.booking.customer_id != self.customer_id
        ):
            errors["customer"] = "Клиент не является владельцем записи."
        if self.requested_starts_at and self.requested_starts_at <= timezone.now():
            errors["requested_starts_at"] = "Новая дата должна быть в будущем."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Перенос #{self.booking_id} — {self.get_status_display()}"


class FAQ(models.Model):
    question = models.CharField(max_length=240)
    answer = models.TextField()
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, null=True, blank=True, related_name="faqs"
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "частый вопрос"
        verbose_name_plural = "Частые вопросы"


class Article(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=180)
    excerpt = models.CharField(max_length=300)
    category = models.CharField(max_length=80)
    reading_time = models.PositiveSmallIntegerField(default=5)
    image = models.CharField(max_length=120, default="look-1.svg")
    uploaded_image = models.ImageField(
        upload_to="journal/", blank=True, validators=[validate_image_size]
    )
    image_alt = models.CharField(max_length=180, blank=True)
    body = models.TextField()
    published_at = models.DateField()
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]

    @property
    def image_url(self):
        return (
            self.uploaded_image.url
            if self.uploaded_image
            else staticfiles_storage.url(f"studio/img/{self.image}")
        )

    def __str__(self):
        return self.title


class GalleryItem(models.Model):
    title = models.CharField(max_length=140)
    category = models.CharField(max_length=80)
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_items",
    )
    master = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_items",
    )
    image = models.ImageField(
        upload_to="gallery/", blank=True, validators=[validate_image_size]
    )
    fallback_image = models.CharField(max_length=120, default="details.svg")
    alt = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "работа"
        verbose_name_plural = "Галерея"

    @property
    def image_url(self):
        return (
            self.image.url
            if self.image
            else staticfiles_storage.url(f"studio/img/{self.fallback_image}")
        )


class Review(models.Model):
    name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField()
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    master = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    date = models.DateField()
    source = models.CharField(max_length=80, default="Демо")
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-date"]
        verbose_name = "отзыв"
        verbose_name_plural = "Отзывы"


class NotificationLog(models.Model):
    TYPES = [
        ("booking_created", "Создание записи"),
        ("booking_confirmed", "Подтверждение"),
        ("booking_cancelled", "Отмена"),
        ("reschedule_requested", "Запрос переноса"),
        ("reschedule_approved", "Перенос подтверждён"),
        ("reschedule_rejected", "Перенос отклонён"),
        ("login", "Вход"),
        ("reminder", "Напоминание"),
    ]
    CHANNELS = [("email", "Email"), ("telegram", "Telegram")]
    STATUSES = [("pending", "Ожидает"), ("sent", "Отправлено"), ("failed", "Ошибка")]
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    type = models.CharField(max_length=30, choices=TYPES)
    channel = models.CharField(max_length=20, choices=CHANNELS)
    recipient = models.CharField(max_length=200)
    text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUSES, default="pending")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=160, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "уведомление"
        verbose_name_plural = "Уведомления"
