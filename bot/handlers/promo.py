"""Promokod kiritish (so'm beradi)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database import db
from bot.handlers.user import show_subscription_gate
from bot.utils.states import PromoRedeem
from bot.utils.texts import t

router = Router(name="promo")


@router.message(F.text.in_({"🎁 Promokod", "🎁 Промокод"}))
async def ask_promo(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    if user is None or not user.is_registered:
        await message.answer(t("not_registered", lang))
        return
    if not await show_subscription_gate(message, lang):
        return
    await state.set_state(PromoRedeem.code)
    await message.answer(t("promo_ask", lang))


@router.message(PromoRedeem.code, F.text)
async def redeem_promo(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"

    code = message.text.strip()
    # Menyu tugmasi bosilsa — bekor qilamiz
    menu_texts = {
        "💰 Balans", "💰 Баланс", "🎯 Vazifalar", "🎯 Задания",
        "👥 Referal", "👥 Реферал", "🎁 Promokod", "🎁 Промокод",
        "💳 Balansni to'ldirish", "💳 Пополнить баланс",
        "🌐 Til", "🌐 Язык", "🛠 Admin panel", "🛠 Админ панель",
    }
    if code in menu_texts:
        await state.clear()
        return

    status, reward = await db.redeem_promocode(code, message.from_user.id)
    await state.clear()

    msg_key = {
        "ok": "promo_ok",
        "not_found": "promo_not_found",
        "already": "promo_already",
        "limit": "promo_limit",
        "inactive": "promo_inactive",
    }.get(status, "promo_not_found")

    if status == "ok":
        await message.answer(t(msg_key, lang, reward=reward))
    else:
        await message.answer(t(msg_key, lang))
