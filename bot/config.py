"""Loyiha konfiguratsiyasi — .env fayldan o'qiladi."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()
    ids: list[int] = []
    for part in raw.replace(" ", "").split(","):
        if part:
            try:
                ids.append(int(part))
            except ValueError:
                continue
    return ids


@dataclass(frozen=True)
class Config:
    # Telegram
    bot_token: str = os.getenv("BOT_TOKEN", "").strip()
    admin_ids: list[int] = field(default_factory=_get_admin_ids)

    # Database
    db_url: str = os.getenv("DB_URL", "sqlite+aiosqlite:///bonus_bot.db").strip()

    # Referal (so'm)
    referral_join_bonus: int = _get_int("REFERRAL_JOIN_BONUS", 1000)
    # Egaga HAR ZADANIYA uchun beriladigan bonus (3-kun oynasi ichida)
    referral_task_bonus: int = _get_int("REFERRAL_TASK_BONUS", 2000)
    referral_task_threshold: int = _get_int("REFERRAL_TASK_THRESHOLD", 1)
    # Referal ro'yxatdan o'tgach shu KUN ichida zadaniya bajarsa egaga bonus
    referral_window_days: int = _get_int("REFERRAL_WINDOW_DAYS", 3)
    # Zadaniya bajargach shu KUN ichida chiqib ketsa bonus qaytariladi
    unsub_check_days: int = _get_int("UNSUB_CHECK_DAYS", 7)

    # Balans
    min_topup: int = _get_int("MIN_TOPUP", 1000)

    # Payme
    payme_merchant_id: str = os.getenv("PAYME_MERCHANT_ID", "").strip()
    payme_secret_key: str = os.getenv("PAYME_SECRET_KEY", "").strip()
    payme_checkout_url: str = os.getenv(
        "PAYME_CHECKOUT_URL", "https://checkout.paycom.uz"
    ).strip().rstrip("/")

    # Webhook
    webhook_host: str = os.getenv("WEBHOOK_HOST", "0.0.0.0").strip()
    webhook_port: int = _get_int("WEBHOOK_PORT", 8080)
    payme_endpoint_path: str = os.getenv("PAYME_ENDPOINT_PATH", "/payme").strip()

    @property
    def owner_id(self) -> int | None:
        return self.admin_ids[0] if self.admin_ids else None

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids

    @property
    def sqlite_path(self) -> str | None:
        """DB_URL dan SQLite fayl yo'lini ajratib oladi (backup uchun).
        Masalan: sqlite+aiosqlite:///bonus_bot.db -> bonus_bot.db"""
        url = self.db_url
        if "sqlite" not in url:
            return None
        # sxemadan keyingi qismni olamiz
        _, _, rest = url.partition("://")
        # aiosqlite'da yo'l '///fayl' ko'rinishida — bosh '/' larni ajratamiz
        path = rest.lstrip("/")
        return path or None


config = Config()
