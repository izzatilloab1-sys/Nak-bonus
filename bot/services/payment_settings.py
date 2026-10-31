"""To'lov sozlamalari — admin paneldan boshqariladi (DB'da saqlanadi).

3 usul: Payme, Click, Karta (avto).
DB'dagi qiymat .env dan USTUN turadi (admin panelдан kiritilsa).

DB `settings` jadvalidagi kalitlar:
  pay_payme_enabled / pay_payme_merchant_id / pay_payme_key
  pay_click_enabled / pay_click_service_id / pay_click_merchant_id / pay_click_key
  pay_card_enabled  / pay_card_number / pay_card_holder
"""
from __future__ import annotations

from bot.config import config
from bot.database import db


async def _get(key: str, env_default: str = "") -> str:
    """DB'dan oladi; bo'sh bo'lsa .env default'ga qaytadi."""
    val = await db.get_setting(key)
    if val is not None and val != "":
        return val
    return env_default


async def _get_bool(key: str, default: bool = False) -> bool:
    val = await db.get_setting(key)
    if val is None:
        return default
    return val == "1"


# ------------------------------------------------------------------ #
#  PAYME
# ------------------------------------------------------------------ #
async def payme_enabled() -> bool:
    # Default: merchant_id va key bo'lsa yoqilgan hisoblanadi
    explicit = await db.get_setting("pay_payme_enabled")
    if explicit is not None:
        return explicit == "1"
    mid = await payme_merchant_id()
    key = await payme_key()
    return bool(mid and key)


async def payme_merchant_id() -> str:
    return await _get("pay_payme_merchant_id", config.payme_merchant_id)


async def payme_key() -> str:
    return await _get("pay_payme_key", config.payme_secret_key)


# ------------------------------------------------------------------ #
#  CLICK
# ------------------------------------------------------------------ #
async def click_enabled() -> bool:
    explicit = await db.get_setting("pay_click_enabled")
    if explicit is not None:
        return explicit == "1"
    sid = await click_service_id()
    key = await click_secret_key()
    return bool(sid and key)


async def click_service_id() -> str:
    import os
    return await _get("pay_click_service_id", os.getenv("CLICK_SERVICE_ID", "").strip())


async def click_merchant_id() -> str:
    import os
    return await _get("pay_click_merchant_id", os.getenv("CLICK_MERCHANT_ID", "").strip())


async def click_secret_key() -> str:
    import os
    return await _get("pay_click_key", os.getenv("CLICK_SECRET_KEY", "").strip())


# ------------------------------------------------------------------ #
#  KARTA (avto — Telegram bildirishnomasidan aniqlash)
# ------------------------------------------------------------------ #
async def card_enabled() -> bool:
    explicit = await db.get_setting("pay_card_enabled")
    if explicit is not None:
        return explicit == "1"
    return bool(await card_number())


async def card_number() -> str:
    import os
    return await _get("pay_card_number", os.getenv("CARD_NUMBER", "").strip())


async def card_holder() -> str:
    import os
    return await _get("pay_card_holder", os.getenv("CARD_HOLDER", "").strip())


# ------------------------------------------------------------------ #
#  Umumiy
# ------------------------------------------------------------------ #
async def set_value(key: str, value: str | None) -> None:
    await db.set_setting(key, value)


async def any_enabled() -> bool:
    return (
        await payme_enabled()
        or await click_enabled()
        or await card_enabled()
    )


async def enabled_methods() -> list[str]:
    methods = []
    if await payme_enabled():
        methods.append("payme")
    if await click_enabled():
        methods.append("click")
    if await card_enabled():
        methods.append("card")
    return methods
