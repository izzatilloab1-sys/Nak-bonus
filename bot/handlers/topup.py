"""Balansni to'ldirish — Payme Checkout havolasi orqali."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.handlers.user import show_subscription_gate
from bot.keyboards.user_kb import pay_link_kb, topup_amounts_kb
from bot.services.payme import generate_checkout_link
from bot.utils.states import TopUp
from bot.utils.texts import t

router = Router(name="topup")


@router.message(F.text.in_({"💳 Balansni to'ldirish", "💳 Пополнить баланс"}))
async def topup_menu(message: Message) -> None:
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    if user is None or not user.is_registered:
        await message.answer(t("not_registered", lang))
        return
    if not await show_subscription_gate(message, lang):
        return

    # Payme sozlanmaganini oldini olish uchun ogohlantirish
    if not config.payme_merchant_id:
        await message.answer(
            "⚠️ To'lov tizimi hali sozlanmagan. Administratorga murojaat qiling."
            if lang == "uz"
            else "⚠️ Платёжная система ещё не настроена. Обратитесь к администратору."
        )
        return

    await message.answer(
        t("topup_choose", lang, min=config.min_topup),
        reply_markup=topup_amounts_kb(lang),
    )


@router.callback_query(F.data.startswith("topup:"))
async def topup_selected(call: CallbackQuery, state: FSMContext) -> None:
    user = await db.get_user(call.from_user.id)
    lang = (user.language if user else "uz") or "uz"

    choice = call.data.split(":", 1)[1]

    if choice == "custom":
        await state.set_state(TopUp.amount)
        await call.message.answer(t("topup_ask_custom", lang))
        await call.answer()
        return

    try:
        amount = int(choice)
    except ValueError:
        await call.answer()
        return

    await _create_and_send_link(call.message, call.from_user.id, amount, lang)
    await call.answer()


@router.message(TopUp.amount, F.text)
async def topup_custom_amount(message: Message, state: FSMContext) -> None:
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"

    raw = message.text.strip().replace(" ", "").replace(",", "")
    if not raw.isdigit():
        await message.answer(t("topup_invalid", lang))
        return
    amount = int(raw)
    if amount < config.min_topup:
        await message.answer(t("topup_too_small", lang, min=config.min_topup))
        return

    await state.clear()
    await _create_and_send_link(message, message.from_user.id, amount, lang)


async def _create_and_send_link(
    message: Message, user_id: int, amount: int, lang: str
) -> None:
    """Order yaratadi va Payme Checkout havolasini yuboradi."""
    order = await db.create_order(user_id, amount)
    url = generate_checkout_link(order.id, amount)
    await message.answer(
        t("topup_link", lang, amount=amount),
        reply_markup=pay_link_kb(url, lang),
    )
