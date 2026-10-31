"""Click SHOP API integratsiyasi (Prepare / Complete).

Click ikki bosqichli callback yuboradi:
  action=0  Prepare  — to'lovni tayyorlash (tekshirish)
  action=1  Complete — to'lovni yakunlash (balansni to'ldirish)

Imzo (sign_string) MD5 orqali tekshiriladi:
  Prepare : md5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id
                + amount + action + sign_time)
  Complete: md5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id
                + merchant_prepare_id + amount + action + sign_time)

Sozlamalar admin paneldan (DB) yoki .env dan olinadi.
"""
from __future__ import annotations

import hashlib
import logging

from bot.database import db
from bot.services import payment_settings

logger = logging.getLogger("bot.click")

# Click xatolik kodlari
CLICK_SUCCESS = 0
ERR_SIGN_CHECK = -1          # imzo noto'g'ri
ERR_INVALID_AMOUNT = -2      # summa noto'g'ri
ERR_ACTION_NOT_FOUND = -3    # action topilmadi
ERR_ALREADY_PAID = -4        # allaqachon to'langan
ERR_TRANSACTION_CANCELLED = -9
ERR_USER_NOT_FOUND = -5      # buyurtma topilmadi
ERR_TRANSACTION_NOT_FOUND = -6
ERR_BAD_REQUEST = -8


def _md5(*parts) -> str:
    raw = "".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


async def _verify_prepare_sign(data: dict, secret_key: str) -> bool:
    expected = _md5(
        data.get("click_trans_id", ""),
        data.get("service_id", ""),
        secret_key,
        data.get("merchant_trans_id", ""),
        data.get("amount", ""),
        data.get("action", ""),
        data.get("sign_time", ""),
    )
    return expected == data.get("sign_string", "")


async def _verify_complete_sign(data: dict, secret_key: str) -> bool:
    expected = _md5(
        data.get("click_trans_id", ""),
        data.get("service_id", ""),
        secret_key,
        data.get("merchant_trans_id", ""),
        data.get("merchant_prepare_id", ""),
        data.get("amount", ""),
        data.get("action", ""),
        data.get("sign_time", ""),
    )
    return expected == data.get("sign_string", "")


def _err(data: dict, code: int, note: str) -> dict:
    return {
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "error": code,
        "error_note": note,
    }


# ------------------------------------------------------------------ #
#  Prepare (action=0)
# ------------------------------------------------------------------ #
async def handle_prepare(data: dict) -> dict:
    secret_key = await payment_settings.click_secret_key()
    if not secret_key or not await _verify_prepare_sign(data, secret_key):
        return _err(data, ERR_SIGN_CHECK, "Sign check failed")

    order_id_raw = data.get("merchant_trans_id")
    try:
        order_id = int(order_id_raw)
    except (ValueError, TypeError):
        return _err(data, ERR_USER_NOT_FOUND, "Order not found")

    order = await db.get_order(order_id)
    if order is None:
        return _err(data, ERR_USER_NOT_FOUND, "Order not found")
    if order.state == "PAID":
        return _err(data, ERR_ALREADY_PAID, "Already paid")
    if order.state == "CANCELLED":
        return _err(data, ERR_TRANSACTION_CANCELLED, "Order cancelled")

    # Summa (Click so'mda yuboradi)
    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return _err(data, ERR_INVALID_AMOUNT, "Invalid amount")
    if int(amount) != int(order.amount):
        return _err(data, ERR_INVALID_AMOUNT, "Invalid amount")

    return {
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        # Prepare ID sifatida order_id ni ishlatamiz
        "merchant_prepare_id": order_id,
        "error": CLICK_SUCCESS,
        "error_note": "Success",
    }


# ------------------------------------------------------------------ #
#  Complete (action=1)
# ------------------------------------------------------------------ #
async def handle_complete(data: dict, notifier=None) -> dict:
    secret_key = await payment_settings.click_secret_key()
    if not secret_key or not await _verify_complete_sign(data, secret_key):
        return _err(data, ERR_SIGN_CHECK, "Sign check failed")

    order_id_raw = data.get("merchant_trans_id")
    try:
        order_id = int(order_id_raw)
    except (ValueError, TypeError):
        return _err(data, ERR_USER_NOT_FOUND, "Order not found")

    order = await db.get_order(order_id)
    if order is None:
        return _err(data, ERR_USER_NOT_FOUND, "Order not found")

    # Click xato (error < 0) yuborsa — bekor qilamiz
    try:
        click_error = int(data.get("error", 0))
    except (ValueError, TypeError):
        click_error = 0
    if click_error < 0:
        await db.cancel_order(order_id)
        return _err(data, ERR_TRANSACTION_CANCELLED, "Payment cancelled")

    if order.state == "PAID":
        # Idempotent — allaqachon to'langan
        return {
            "click_trans_id": data.get("click_trans_id"),
            "merchant_trans_id": data.get("merchant_trans_id"),
            "merchant_confirm_id": order_id,
            "error": CLICK_SUCCESS,
            "error_note": "Already paid",
        }

    # Atomik: PENDING -> PAID va balansni to'ldiramiz
    paid = await db.mark_order_paid(order_id)
    if paid is None:
        return _err(data, ERR_TRANSACTION_CANCELLED, "Cannot complete")

    # Foydalanuvchiga xabar
    if notifier is not None:
        try:
            await notifier(paid.user_id, paid.amount)
        except Exception:
            pass

    return {
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "merchant_confirm_id": order_id,
        "error": CLICK_SUCCESS,
        "error_note": "Success",
    }


async def handle_callback(data: dict, notifier=None) -> dict:
    """Click callback — action'ga qarab Prepare yoki Complete."""
    try:
        action = int(data.get("action", -1))
    except (ValueError, TypeError):
        return _err(data, ERR_ACTION_NOT_FOUND, "Action not found")

    if action == 0:
        return await handle_prepare(data)
    elif action == 1:
        return await handle_complete(data, notifier)
    return _err(data, ERR_ACTION_NOT_FOUND, "Action not found")
