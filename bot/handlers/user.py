"""Asosiy foydalanuvchi handlerlari: menyu, balans, referal, majburiy obuna."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.keyboards.user_kb import (
    language_kb,
    main_menu_kb,
    subscription_kb,
)
from bot.services.subscription import check_all_required
from bot.utils.texts import t

router = Router(name="user")


async def _require_registered(message: Message) -> tuple[bool, object, str]:
    """Foydalanuvchi ro'yxatdan o'tganmi? (ok, user, lang)."""
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    if user is None or not user.is_registered:
        await message.answer(t("not_registered", lang))
        return False, user, lang
    return True, user, lang


async def show_subscription_gate(message: Message, lang: str) -> bool:
    """Majburiy obunani tekshiradi. Obuna to'liq bo'lsa True.
    Aks holda kanallar ro'yxatini chiqaradi va False qaytaradi."""
    channels = await db.get_required_channels()
    if not channels:
        return True
    not_sub = await check_all_required(message.bot, channels, message.from_user.id)
    if not not_sub:
        return True
    await message.answer(
        t("must_subscribe", lang),
        reply_markup=subscription_kb(not_sub, lang),
    )
    return False


# ------------------------------------------------------------------ #
#  Majburiy obuna — "Tekshirish"
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery) -> None:
    user = await db.get_user(call.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    channels = await db.get_required_channels()
    not_sub = await check_all_required(call.bot, channels, call.from_user.id)
    if not_sub:
        await call.answer(t("not_subscribed", lang), show_alert=True)
        return
    await call.message.delete()
    await call.message.answer(t("subscribed_ok", lang))
    await call.message.answer(
        t("main_menu", lang),
        reply_markup=main_menu_kb(lang, config.is_admin(call.from_user.id)),
    )
    await call.answer()


# ------------------------------------------------------------------ #
#  Balans
# ------------------------------------------------------------------ #
@router.message(F.text.in_({"💰 Balans", "💰 Баланс"}))
async def show_balance(message: Message) -> None:
    ok, user, lang = await _require_registered(message)
    if not ok:
        return
    if not await show_subscription_gate(message, lang):
        return
    await message.answer(t("balance_info", lang, balance=user.balance))


# ------------------------------------------------------------------ #
#  Referal
# ------------------------------------------------------------------ #
@router.message(F.text.in_({"👥 Referal", "👥 Реферал"}))
async def show_referral(message: Message) -> None:
    ok, user, lang = await _require_registered(message)
    if not ok:
        return
    if not await show_subscription_gate(message, lang):
        return

    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref{user.id}"
    count, _ = await db.get_referral_stats(user.id)

    await message.answer(
        t(
            "referral_info",
            lang,
            join=config.referral_join_bonus,
            task=config.referral_task_bonus,
            count=count,
            link=link,
        ),
        disable_web_page_preview=True,
    )


# ------------------------------------------------------------------ #
#  Til almashtirish
# ------------------------------------------------------------------ #
@router.message(F.text.in_({"🌐 Til", "🌐 Язык"}))
async def change_language(message: Message) -> None:
    ok, user, lang = await _require_registered(message)
    if not ok:
        return
    await message.answer(t("choose_language", lang), reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:"))
async def switch_language(call: CallbackQuery, state: FSMContext) -> None:
    """Menyudan tilni almashtirish (registratsiyadan tashqarida)."""
    cur_state = await state.get_state()
    if cur_state is not None:
        # Registratsiya oqimidagi lang handleri ishlasin
        return
    lang = call.data.split(":", 1)[1]
    if lang not in ("uz", "ru"):
        lang = "uz"
    await db.set_language(call.from_user.id, lang)
    await call.message.edit_text(t("language_set", lang))
    await call.message.answer(
        t("main_menu", lang),
        reply_markup=main_menu_kb(lang, config.is_admin(call.from_user.id)),
    )
    await call.answer()


# ------------------------------------------------------------------ #
#  noop (bosilmaydigan tugmalar)
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "noop")
async def noop_callback(call: CallbackQuery) -> None:
    await call.answer()
