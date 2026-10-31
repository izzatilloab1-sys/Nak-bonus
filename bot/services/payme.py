"""Payme (Paycom) Merchant API — JSON-RPC 2.0 to'liq realizatsiya.

Protokol: https://developer.help.paycom.uz/protokol-merchant-api

Oqim (balans to'ldirish):
    1. Foydalanuvchi summa tanlaydi → DB'da `Order` (PENDING) yaratiladi.
    2. Botда Payme Checkout havolasi beriladi (m, a=tiyin, ac.order_id).
    3. Payme Merchant kabinetidan quyidagi metodlar chaqiriladi:
         CheckPerformTransaction / CreateTransaction / PerformTransaction /
         CancelTransaction / CheckTransaction / GetStatement
    4. PerformTransaction'da foydalanuvchi balansi avtomatik to'ldiriladi.

Barcha pul summalari Payme tomonida TIYIN'da (so'm * 100).
"""
from __future__ import annotations

import base64
import binascii
import time

from bot import database as _db  # noqa: F401  (paket mavjudligi uchun)
from bot.config import config
from bot.database import db

# ------------------------------------------------------------------ #
#  Payme xatolik kodlari (protokol spetsifikatsiyasi)
# ------------------------------------------------------------------ #
#  -32300  Transport    yetkazish xatosi
#  -32700  Parse error  JSON o'qib bo'lmadi
#  -32600  Invalid Request
#  -32601  Method not found
#  -32504  Avtorizatsiya yetarli emas (Basic Auth xato)
#  -31001  Noto'g'ri summa
#  -31003  Tranzaksiya topilmadi
#  -31050..-31099  Buyurtma topilmadi / tartibda emas (maydonga bog'liq)
#  -31007  Buyurtmani bajarib bo'lmaydi (allaqachon to'langan/holat mos emas)
#  -31008  Tranzaksiyani bajarib bo'lmaydi (holat noto'g'ri)
# ------------------------------------------------------------------ #

ERR_AUTH = -32504
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_JSON = -32700
ERR_INVALID_AMOUNT = -31001
ERR_TX_NOT_FOUND = -31003
ERR_CANNOT_PERFORM = -31008
ERR_ALREADY_DONE = -31007
ERR_ORDER_NOT_FOUND = -31050  # ac.order_id topilmadi/noto'g'ri

# Payme tranzaksiya "timeout" — 12 soat (millisekund)
TX_TIMEOUT_MS = 12 * 60 * 60 * 1000


def _localized(uz: str, ru: str, en: str | None = None) -> dict:
    return {"uz": uz, "ru": ru, "en": en or ru}


class PaymeError(Exception):
    """JSON-RPC xatolik sifatida qaytariladigan istisno."""

    def __init__(self, code: int, message: dict | str, data: str | None = None):
        self.code = code
        self.message = message if isinstance(message, dict) else _localized(
            message, message, message
        )
        self.data = data
        super().__init__(str(message))


def check_auth(authorization_header: str | None) -> bool:
    """HTTP Basic Auth: 'Basic base64(Paycom:SECRET_KEY)'."""
    if not authorization_header:
        return False
    try:
        scheme, _, encoded = authorization_header.partition(" ")
        if scheme.lower() != "basic" or not encoded:
            return False
        decoded = base64.b64decode(encoded).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False
    login, _, key = decoded.partition(":")
    return login == "Paycom" and key == config.payme_secret_key


class PaymeMerchant:
    """Payme Merchant API JSON-RPC metodlarini bajaradi."""

    # -------------------------------------------------------------- #
    #  Kirish nuqtasi: JSON-RPC so'rovini bajarish
    # -------------------------------------------------------------- #
    async def handle(self, payload: dict) -> dict:
        """JSON-RPC so'rovni qabul qiladi, {'result': ...} yoki
        {'error': ...} qaytaradi (id bilan)."""
        rpc_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {}) or {}

        try:
            if method == "CheckPerformTransaction":
                result = await self.check_perform_transaction(params)
            elif method == "CreateTransaction":
                result = await self.create_transaction(params)
            elif method == "PerformTransaction":
                result = await self.perform_transaction(params)
            elif method == "CancelTransaction":
                result = await self.cancel_transaction(params)
            elif method == "CheckTransaction":
                result = await self.check_transaction(params)
            elif method == "GetStatement":
                result = await self.get_statement(params)
            else:
                raise PaymeError(
                    ERR_METHOD_NOT_FOUND,
                    _localized("Metod topilmadi", "Метод не найден", "Method not found"),
                )
            return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
        except PaymeError as e:
            err = {"code": e.code, "message": e.message}
            if e.data is not None:
                err["data"] = e.data
            return {"jsonrpc": "2.0", "id": rpc_id, "error": err}

    # -------------------------------------------------------------- #
    #  Yordamchilar
    # -------------------------------------------------------------- #
    async def _resolve_order(self, params: dict):
        """ac.order_id bo'yicha buyurtmani topadi, tekshiradi."""
        account = params.get("account") or {}
        order_id_raw = account.get("order_id")
        if order_id_raw is None:
            raise PaymeError(
                ERR_ORDER_NOT_FOUND,
                _localized(
                    "Buyurtma raqami ko'rsatilmagan",
                    "Номер заказа не указан",
                    "Order id is missing",
                ),
                data="order_id",
            )
        try:
            order_id = int(order_id_raw)
        except (ValueError, TypeError):
            raise PaymeError(
                ERR_ORDER_NOT_FOUND,
                _localized(
                    "Buyurtma raqami noto'g'ri",
                    "Неверный номер заказа",
                    "Invalid order id",
                ),
                data="order_id",
            )
        order = await db.get_order(order_id)
        if order is None:
            raise PaymeError(
                ERR_ORDER_NOT_FOUND,
                _localized(
                    "Buyurtma topilmadi", "Заказ не найден", "Order not found"
                ),
                data="order_id",
            )
        return order

    def _validate_amount(self, order, amount_tiyin: int) -> None:
        """Payme summasi (tiyin) buyurtma summasiga (so'm*100) mos kelishini
        tekshiradi."""
        expected = int(order.amount) * 100
        if int(amount_tiyin) != expected:
            raise PaymeError(
                ERR_INVALID_AMOUNT,
                _localized(
                    "Noto'g'ri summa", "Неверная сумма", "Incorrect amount"
                ),
            )

    # -------------------------------------------------------------- #
    #  1. CheckPerformTransaction
    # -------------------------------------------------------------- #
    async def check_perform_transaction(self, params: dict) -> dict:
        order = await self._resolve_order(params)
        self._validate_amount(order, params.get("amount", 0))
        if order.state != "PENDING":
            raise PaymeError(
                ERR_ALREADY_DONE,
                _localized(
                    "Buyurtma allaqachon to'langan yoki bekor qilingan",
                    "Заказ уже оплачен или отменён",
                    "Order is already paid or cancelled",
                ),
            )
        return {"allow": True}

    # -------------------------------------------------------------- #
    #  2. CreateTransaction
    # -------------------------------------------------------------- #
    async def create_transaction(self, params: dict) -> dict:
        paycom_tx_id = params.get("id")
        amount = params.get("amount", 0)
        paycom_time = params.get("time", int(time.time() * 1000))

        # Avval shu tx_id mavjudmi?
        existing = await db.get_transaction_by_paycom_id(paycom_tx_id)
        if existing is not None:
            if existing.state == 1:
                # allaqachon yaratilgan — idempotent javob
                return {
                    "create_time": existing.create_time,
                    "transaction": str(existing.id),
                    "state": existing.state,
                }
            # yaratilgan, lekin boshqa holatda — bajarib bo'lmaydi
            raise PaymeError(
                ERR_CANNOT_PERFORM,
                _localized(
                    "Tranzaksiyani yaratib bo'lmaydi",
                    "Невозможно создать транзакцию",
                    "Unable to create transaction",
                ),
            )

        # Buyurtma + summa tekshiruvi (CheckPerform bilan bir xil shartlar)
        order = await self._resolve_order(params)
        self._validate_amount(order, amount)
        if order.state != "PENDING":
            raise PaymeError(
                ERR_ALREADY_DONE,
                _localized(
                    "Buyurtma allaqachon to'langan yoki bekor qilingan",
                    "Заказ уже оплачен или отменён",
                    "Order is already paid or cancelled",
                ),
            )

        tx = await db.create_transaction(
            paycom_tx_id=paycom_tx_id,
            order_id=order.id,
            amount_tiyin=int(amount),
            paycom_time=int(paycom_time),
        )
        return {
            "create_time": tx.create_time,
            "transaction": str(tx.id),
            "state": tx.state,
        }

    # -------------------------------------------------------------- #
    #  3. PerformTransaction
    # -------------------------------------------------------------- #
    async def perform_transaction(self, params: dict) -> dict:
        paycom_tx_id = params.get("id")
        tx = await db.get_transaction_by_paycom_id(paycom_tx_id)
        if tx is None:
            raise PaymeError(
                ERR_TX_NOT_FOUND,
                _localized(
                    "Tranzaksiya topilmadi",
                    "Транзакция не найдена",
                    "Transaction not found",
                ),
            )

        if tx.state == 2:
            # idempotent
            return {
                "transaction": str(tx.id),
                "perform_time": tx.perform_time,
                "state": tx.state,
            }

        if tx.state != 1:
            raise PaymeError(
                ERR_CANNOT_PERFORM,
                _localized(
                    "Tranzaksiyani bajarib bo'lmaydi",
                    "Невозможно выполнить транзакцию",
                    "Unable to perform transaction",
                ),
            )

        # Timeout tekshiruvi
        if (int(time.time() * 1000) - tx.create_time) > TX_TIMEOUT_MS:
            await db.cancel_transaction(paycom_tx_id, reason=4)
            raise PaymeError(
                ERR_CANNOT_PERFORM,
                _localized(
                    "Tranzaksiya muddati o'tgan",
                    "Срок транзакции истёк",
                    "Transaction timed out",
                ),
            )

        tx = await db.perform_transaction(paycom_tx_id)
        # Foydalanuvchiga xabar beramiz (callback orqali bot)
        await _notify_user_paid(tx)
        return {
            "transaction": str(tx.id),
            "perform_time": tx.perform_time,
            "state": tx.state,
        }

    # -------------------------------------------------------------- #
    #  4. CancelTransaction
    # -------------------------------------------------------------- #
    async def cancel_transaction(self, params: dict) -> dict:
        paycom_tx_id = params.get("id")
        reason = params.get("reason")
        tx = await db.get_transaction_by_paycom_id(paycom_tx_id)
        if tx is None:
            raise PaymeError(
                ERR_TX_NOT_FOUND,
                _localized(
                    "Tranzaksiya topilmadi",
                    "Транзакция не найдена",
                    "Transaction not found",
                ),
            )

        tx = await db.cancel_transaction(paycom_tx_id, reason=int(reason or 0))
        return {
            "transaction": str(tx.id),
            "cancel_time": tx.cancel_time,
            "state": tx.state,
        }

    # -------------------------------------------------------------- #
    #  5. CheckTransaction
    # -------------------------------------------------------------- #
    async def check_transaction(self, params: dict) -> dict:
        paycom_tx_id = params.get("id")
        tx = await db.get_transaction_by_paycom_id(paycom_tx_id)
        if tx is None:
            raise PaymeError(
                ERR_TX_NOT_FOUND,
                _localized(
                    "Tranzaksiya topilmadi",
                    "Транзакция не найдена",
                    "Transaction not found",
                ),
            )
        return {
            "create_time": tx.create_time,
            "perform_time": tx.perform_time,
            "cancel_time": tx.cancel_time,
            "transaction": str(tx.id),
            "state": tx.state,
            "reason": tx.reason,
        }

    # -------------------------------------------------------------- #
    #  6. GetStatement
    # -------------------------------------------------------------- #
    async def get_statement(self, params: dict) -> dict:
        from sqlalchemy import select

        from bot.database.models import Transaction

        start = int(params.get("from", 0))
        end = int(params.get("to", int(time.time() * 1000)))

        async with db.async_session() as session:
            rows = await session.execute(
                select(Transaction).where(
                    Transaction.paycom_time >= start,
                    Transaction.paycom_time <= end,
                )
            )
            txs = list(rows.scalars().all())

        transactions = []
        for tx in txs:
            order = await db.get_order(tx.order_id)
            transactions.append(
                {
                    "id": tx.paycom_tx_id,
                    "time": tx.paycom_time,
                    "amount": tx.amount,
                    "account": {
                        "order_id": str(tx.order_id),
                    },
                    "create_time": tx.create_time,
                    "perform_time": tx.perform_time,
                    "cancel_time": tx.cancel_time,
                    "transaction": str(tx.id),
                    "state": tx.state,
                    "reason": tx.reason,
                    "receivers": None,
                }
            )
        return {"transactions": transactions}


# ------------------------------------------------------------------ #
#  To'lov muvaffaqiyatli bo'lganda foydalanuvchiga xabar
#  (bot obyektini main.py o'rnatadi)
# ------------------------------------------------------------------ #
_bot_notifier = None


def set_bot_notifier(fn) -> None:
    """main.py chaqiradi: PerformTransaction'dan keyin foydalanuvchiga
    xabar yuboradigan coroutine funksiyani o'rnatadi."""
    global _bot_notifier
    _bot_notifier = fn


async def _notify_user_paid(tx) -> None:
    if _bot_notifier is None or tx is None:
        return
    try:
        order = await db.get_order(tx.order_id)
        if order is not None:
            await _bot_notifier(order.user_id, order.amount)
    except Exception:
        # Xabar yuborilmasa ham to'lov muvaffaqiyatli hisoblanadi
        pass


# ------------------------------------------------------------------ #
#  Checkout havolasini yaratish
# ------------------------------------------------------------------ #
def generate_checkout_link(order_id: int, amount_som: int) -> str:
    """Payme Checkout havolasini yaratadi.

    Format: {checkout_url}/{base64(m=...;ac.order_id=...;a=tiyin)}
    """
    amount_tiyin = amount_som * 100
    raw = (
        f"m={config.payme_merchant_id};"
        f"ac.order_id={order_id};"
        f"a={amount_tiyin}"
    )
    encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    return f"{config.payme_checkout_url}/{encoded}"
