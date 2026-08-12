from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone

from studio.models import Customer, LoginToken


@dataclass(frozen=True)
class LoginCredentials:
    raw_token: str
    code: str
    record: LoginToken


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_login_token(customer: Customer) -> LoginCredentials:
    """Issue one token and invalidate older unused credentials."""
    LoginToken.objects.filter(customer=customer, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    raw_token = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(1_000_000):06d}"
    record = LoginToken.objects.create(
        customer=customer,
        token_hash=hash_secret(raw_token),
        code_hash=hash_secret(code),
        expires_at=timezone.now() + timedelta(minutes=settings.LOGIN_TOKEN_MINUTES),
    )
    return LoginCredentials(raw_token=raw_token, code=code, record=record)


def consume_magic_token(raw_token: str) -> Customer | None:
    record = LoginToken.objects.filter(token_hash=hash_secret(raw_token)).first()
    if not record or not record.valid:
        return None
    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return record.customer


def consume_login_code(email: str, code: str) -> Customer | None:
    record = (
        LoginToken.objects.filter(
            customer__email__iexact=email,
            used_at__isnull=True,
        )
        .select_related("customer")
        .order_by("-created_at")
        .first()
    )
    if not record or not record.valid:
        return None
    if not secrets.compare_digest(record.code_hash, hash_secret(code)):
        record.attempts += 1
        record.save(update_fields=["attempts"])
        return None
    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return record.customer


def current_customer(request):
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return None
    return Customer.objects.filter(pk=customer_id).first()


def customer_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        customer = current_customer(request)
        if customer is None:
            request.session["login_next"] = request.get_full_path()
            return redirect("studio:login_request")
        request.customer = customer
        return view(request, *args, **kwargs)

    return wrapped
