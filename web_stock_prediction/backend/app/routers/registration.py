import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

CODE_TTL_SECONDS = 10 * 60
RESEND_DELAY_SECONDS = 60
MAX_VERIFY_ATTEMPTS = 5
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TOKEN_SECRET = (
    os.getenv("REGISTRATION_TOKEN_SECRET")
    or os.getenv("DB_PASSWORD")
    or "stock-predictor-registration-local-secret"
)
CODE_SECRET = os.getenv("REGISTRATION_CODE_SECRET") or TOKEN_SECRET

_pending_codes: dict[str, dict[str, float | int | str]] = {}
_pending_lock = threading.Lock()


class EmailRequest(BaseModel):
    email: str


class VerifyRequest(BaseModel):
    email: str
    code: str


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Email không hợp lệ.")
    return email


def _hash_code(email: str, code: str) -> str:
    return hmac.new(
        CODE_SECRET.encode("utf-8"),
        f"{email}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _send_verification_email(email: str, code: str) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username
    port = int(os.getenv("SMTP_PORT", "587"))
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not host or not from_email:
        raise RuntimeError("SMTP chưa được cấu hình.")

    message = EmailMessage()
    message["Subject"] = "Mã xác minh Stock Predictor"
    message["From"] = from_email
    message["To"] = email
    message.set_content(
        "Mã xác minh đăng ký Stock Predictor của bạn là:\n\n"
        f"{code}\n\n"
        "Mã có hiệu lực trong 10 phút. Không chia sẻ mã này cho người khác."
    )

    context = ssl.create_default_context()
    if use_ssl:
        smtp_connection = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
    else:
        smtp_connection = smtplib.SMTP(host, port, timeout=15)

    with smtp_connection as smtp:
        if not use_ssl:
            smtp.ehlo()
            if use_tls:
                smtp.starttls(context=context)
                smtp.ehlo()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


def _encode_token(email: str) -> str:
    payload = {
        "email": email,
        "exp": int(time.time()) + (365 * 24 * 60 * 60),
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def _decode_token(token: str) -> dict:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(
            TOKEN_SECRET.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        padded = encoded + ("=" * (-len(encoded) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng ký không hợp lệ hoặc đã hết hạn.",
        )


def _ensure_subscriber_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS public.signal_subscribers (
                email VARCHAR(254) PRIMARY KEY,
                verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
    )


@router.post("/request-code")
def request_code(payload: EmailRequest):
    email = _normalize_email(payload.email)
    now = time.time()

    with _pending_lock:
        current = _pending_codes.get(email)
        if current and now - float(current["sent_at"]) < RESEND_DELAY_SECONDS:
            wait_seconds = int(RESEND_DELAY_SECONDS - (now - float(current["sent_at"])))
            raise HTTPException(
                status_code=429,
                detail=f"Vui lòng chờ {max(wait_seconds, 1)} giây trước khi gửi lại mã.",
            )

    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        _send_verification_email(email, code)
    except (OSError, RuntimeError, smtplib.SMTPException) as exc:
        logger.exception("Unable to send registration email")
        raise HTTPException(
            status_code=503,
            detail="Chưa thể gửi email xác minh. Vui lòng kiểm tra cấu hình SMTP.",
        ) from exc

    with _pending_lock:
        _pending_codes[email] = {
            "code_hash": _hash_code(email, code),
            "expires_at": now + CODE_TTL_SECONDS,
            "sent_at": now,
            "attempts": 0,
        }

    return {"message": "Mã xác minh đã được gửi tới email của bạn.", "expires_in": CODE_TTL_SECONDS}


@router.post("/verify")
def verify_code(payload: VerifyRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    code = payload.code.strip()
    if not re.fullmatch(r"\d{6}", code):
        raise HTTPException(status_code=422, detail="Mã xác minh phải gồm 6 chữ số.")

    now = time.time()
    with _pending_lock:
        pending = _pending_codes.get(email)
        if not pending or float(pending["expires_at"]) < now:
            _pending_codes.pop(email, None)
            raise HTTPException(status_code=400, detail="Mã xác minh không tồn tại hoặc đã hết hạn.")

        attempts = int(pending["attempts"])
        if attempts >= MAX_VERIFY_ATTEMPTS:
            _pending_codes.pop(email, None)
            raise HTTPException(status_code=429, detail="Bạn đã nhập sai quá nhiều lần. Vui lòng gửi mã mới.")

        if not hmac.compare_digest(str(pending["code_hash"]), _hash_code(email, code)):
            pending["attempts"] = attempts + 1
            raise HTTPException(status_code=400, detail="Mã xác minh không đúng.")

        _pending_codes.pop(email, None)

    _ensure_subscriber_table(db)
    db.execute(
        text(
            """
            INSERT INTO public.signal_subscribers (email, verified_at, is_active)
            VALUES (:email, NOW(), TRUE)
            ON CONFLICT (email)
            DO UPDATE SET verified_at = NOW(), is_active = TRUE
            """
        ),
        {"email": email},
    )
    db.commit()

    return {
        "message": "Đăng ký thành công.",
        "access_token": _encode_token(email),
        "email": email,
    }


@router.get("/status")
def registration_status(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"registered": False}

    payload = _decode_token(authorization[7:].strip())
    _ensure_subscriber_table(db)
    subscriber = db.execute(
        text(
            """
            SELECT email
            FROM public.signal_subscribers
            WHERE email = :email AND is_active = TRUE
            """
        ),
        {"email": payload["email"]},
    ).first()
    db.commit()

    return {
        "registered": subscriber is not None,
        "email": payload["email"] if subscriber else None,
    }
