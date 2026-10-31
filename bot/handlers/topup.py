"""Balansni to'ldirish — 3 usul: Payme, Click, Karta (avto).

Usullar admin paneldan yoqiladi/o'chiriladi. Foydalanuvchiga faqat YOQILGAN
usullar tugma bo'lib chiqadi.
"""
from __future__ import annotations

from urllib.parse import quote

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import config
from bot.database import db
from bot.handlers.user import show_subscription_gate
from bot.keyboards.user_kb import pay_link_kb, topup_amounts_kb
from bot.services import payme as payme_service
from bot.services import payment_settings
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

    # Hech qanday usul yoqilmagan bo'lsa — ogohlantirish
    if not await payment_settings.any_enabled():
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

    await _ask_method(call.message, amount, lang)
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
    await _ask_method(message, amount, lang)


async def _ask_method(message: Message, amount: int, lang: str) -> None:
    """Yoqilgan to'lov usullarini tugma qilib ko'rsatadi."""
    methods = await payment_settings.enabled_methods()
    if not methods:
        await message.answer(
            "⚠️ To'lov tizimi sozlanmagan."
            if lang == "uz"
            else "⚠️ Платёжная система не настроена."
        )
        return

    rows = []
    if "payme" in methods:
        rows.append([InlineKeyboardButton(
            text="💳 Payme", callback_data=f"paym:payme:{amount}"
        )])
    if "click" in methods:
        rows.append([InlineKeyboardButton(
            text="💳 Click", callback_data=f"paym:click:{amount}"
        )])
    if "card" in methods:
        rows.append([InlineKeyboardButton(
            text="💵 Karta", callback_data=f"paym:card:{amount}"
        )])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    txt = (
        f"💳 To'lov usulini tanlang:\n\n💰 Summa: <b>{amount:,} so'm</b>"
        if lang == "uz"
        else f"💳 Выберите способ оплаты:\n\n💰 Сумма: <b>{amount:,} сум</b>"
    )
    await message.answer(txt, reply_markup=kb)


@router.callback_query(F.data.startswith("paym:"))
async def topup_method_chosen(call: CallbackQuery) -> None:
    user = await db.get_user(call.from_user.id)
    lang = (user.language if user else "uz") or "uz"

    _, method, amount_raw = call.data.split(":", 2)
    amount = int(amount_raw)

    # Har usul uchun bitta order yaratamiz
    order = await db.create_order(call.from_user.id, amount)

    if method == "payme":
        if not await payment_settings.payme_enabled():
            await call.answer("Payme o'chirilgan", show_alert=True)
            return
        url = await payme_service.generate_checkout_link(order.id, amount)
        await call.message.answer(
            t("topup_link", lang, amount=amount),
            reply_markup=pay_link_kb(url, lang),
        )

    elif method == "click":
        if not await payment_settings.click_enabled():
            await call.answer("Click o'chirilgan", show_alert=True)
            return
        url = await _build_click_link(order.id, amount)
        if url is None:
            await call.answer()
            await call.message.answer(
                "⚠️ Click sozlanmagan." if lang == "uz"
                else "⚠️ Click не настроен."
            )
            return
        await call.message.answer(
            t("topup_link", lang, amount=amount),
            reply_markup=pay_link_kb(url, lang),
        )

    elif method == "card":
        if not await payment_settings.card_enabled():
            await call.answer("Karta o'chirilgan", show_alert=True)
            return
        card = await payment_settings.card_number()
        holder = await payment_settings.card_holder()
        holder_line = f"\n👤 {holder}" if holder else ""
        if lang == "ru":
            txt = (
                f"💵 <b>Оплата на карту</b>\n\n"
                f"💰 Сумма: <b>{amount:,} сум</b>\n"
                f"💳 Карта: <code>{card}</code>{holder_line}\n\n"
                f"Переведите точную сумму на карту. После оплаты администратор "
                f"подтвердит, и баланс будет пополнен.\n"
                f"🧾 Номер заказа: <code>{order.id}</code>"
            )
        else:
            txt = (
                f"💵 <b>Kartaga to'lov</b>\n\n"
                f"💰 Summa: <b>{amount:,} so'm</b>\n"
                f"💳 Karta: <code>{card}</code>{holder_line}\n\n"
                f"Aniq summani kartaga o'tkazing. To'lovdan so'ng admin tasdiqlaydi "
                f"va balansingiz to'ldiriladi.\n"
                f"🧾 Buyurtma raqami: <code>{order.id}</code>"
            )
        await call.message.answer(txt)
        # Adminlarga xabar
        await _notify_admins_card(call, order, amount)

    await call.answer()


async def _build_click_link(order_id: int, amount: int) -> str | None:
    """Click to'lov havolasini yaratadi."""
    service_id = await payment_settings.click_service_id()
    merchant_id = await payment_settings.click_merchant_id()
    if not service_id or not merchant_id:
        return None
    # Click standart to'lov havolasi
    return (
        "https://my.click.uz/services/pay"
        f"?service_id={quote(service_id)}"
        f"&merchant_id={quote(merchant_id)}"
        f"&amount={amount}"
        f"&transaction_param={order_id}"
    )


async def _notify_admins_card(call: CallbackQuery, order, amount: int) -> None:
    user = call.from_user
    uname = f"@{user.username}" if user.username else "—"
    txt = (
        f"💵 <b>Karta to'lovi (tasdiqlash kerak)</b>\n\n"
        f"👤 Foydalanuvchi: <code>{user.id}</code> ({uname})\n"
        f"💰 Summa: <b>{amount:,} so'm</b>\n"
        f"🧾 Buyurtma: <code>{order.id}</code>\n\n"
        f"To'lov kelganini tekshirib, tasdiqlang:"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ To'landi", callback_data=f"cardok:{order.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Bekor", callback_data=f"cardno:{order.id}"
                ),
            ]
        ]
    )
    for admin_id in config.admin_ids:
        try:
            await call.bot.send_message(admin_id, txt, reply_markup=kb)
        except Exception:
            pass
