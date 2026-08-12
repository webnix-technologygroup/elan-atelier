import re

from django import forms
from django.utils import timezone

from .models import Service, TeamMember

PHONE_MIN_DIGITS = 10
PHONE_MAX_DIGITS = 15


def normalize_phone(value: str) -> str:
    """Return a stable E.164-like value containing one plus and digits only."""
    digits = "".join(re.findall(r"\d", value or ""))
    if not PHONE_MIN_DIGITS <= len(digits) <= PHONE_MAX_DIGITS:
        raise forms.ValidationError(
            "Укажите международный номер длиной от 10 до 15 цифр."
        )
    return f"+{digits}"


class BookingForm(forms.Form):
    service = forms.ModelChoiceField(label="Услуга", queryset=Service.objects.none())
    master = forms.ModelChoiceField(
        label="Мастер",
        queryset=TeamMember.objects.none(),
        required=False,
        empty_label="Любой подходящий мастер",
    )
    date = forms.DateField(label="Дата", widget=forms.DateInput(attrs={"type": "date"}))
    time = forms.TimeField(label="Время", widget=forms.HiddenInput())
    selected_master = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    name = forms.CharField(label="Имя", max_length=120)
    phone = forms.CharField(label="Телефон", max_length=40)
    email = forms.EmailField(label="Email")
    message = forms.CharField(
        label="Комментарий",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    consent = forms.BooleanField(label="Согласие с политикой")
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        service_value = self.data.get("service") or self.initial.get("service")
        service_id = getattr(service_value, "pk", service_value)
        if service_id:
            self.fields["master"].queryset = TeamMember.objects.filter(
                is_active=True,
                online_booking=True,
                services=service_id,
            ).distinct()
        else:
            self.fields["master"].queryset = TeamMember.objects.none()

    def clean_phone(self) -> str:
        return normalize_phone(self.cleaned_data["phone"])

    def clean(self):
        data = super().clean()
        if data.get("website"):
            raise forms.ValidationError("Не удалось отправить форму.")
        selected_date = data.get("date")
        today = timezone.localdate()
        if selected_date and not today <= selected_date <= today + timezone.timedelta(
            days=60
        ):
            self.add_error("date", "Выберите дату в пределах 60 дней.")
        return data


class LoginRequestForm(forms.Form):
    email = forms.EmailField(label="Email")


class LoginCodeForm(forms.Form):
    email = forms.EmailField(widget=forms.HiddenInput())
    code = forms.CharField(
        label="Одноразовый код",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric"}),
    )


class CancelBookingForm(forms.Form):
    reason = forms.CharField(
        label="Причина отмены",
        min_length=3,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class RescheduleForm(forms.Form):
    date = forms.DateField(
        label="Новая дата", widget=forms.DateInput(attrs={"type": "date"})
    )
    time = forms.TimeField(label="Новое время", widget=forms.HiddenInput())
    comment = forms.CharField(
        label="Комментарий",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_date(self):
        value = self.cleaned_data["date"]
        today = timezone.localdate()
        if not today <= value <= today + timezone.timedelta(days=60):
            raise forms.ValidationError("Выберите дату в пределах 60 дней.")
        return value
