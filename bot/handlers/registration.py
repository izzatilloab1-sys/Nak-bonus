"""Ro'yxatdan o'tish: til tanlash + telefon raqam (faqat tugma orqali)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.keyboards.user_kb import (
    language_kb,
    main_menu_kb,
    phone_request_kb,
    remove_kb,
)
from bot.utils.states import Registration
from bot.utils.texts import t

router = Router(name="registration")


def _parse_referral(args: str | None) -> int | None:
    """/start <ref> dan referal ID ni ajratadi. 'ref123' yoki '123'."""
    if not args:
        return None
    args = args.strip()
    if args.startswith("ref"):
        args = args[3:]
    if args.isdigit():
        return int(args)
    return None


@router.message(CommandStart(deep_link=True))
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command=None) -> None:
    await state.clear()

    # Referal argumentini ajratamiz
    referred_by = None
    if command is not None and getattr(command, "args", None):
        referred_by = _parse_referral(command.args)

    user = await db.create_user_if_absent(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        referred_by=referred_by,
    )

    # Allaqachon ro'yxatdan o'tgan bo'lsa — to'g'ridan-to'g'ri menyu
    if user.is_registered:
        lang = user.language or "uz"
        await message.answer(
            t("main_menu", lang),
            reply_markup=main_menu_kb(lang, config.is_admin(user.id)),
        )
        return

    # Aks holda — til tanlashdan boshlaymiz
    await state.set_state(Registration.language)
    await message.answer(t("choose_language", "uz"), reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:"), Registration.language)
async def choose_language(call: CallbackQuery, state: FSMContext) -> None:
    lang = call.data.split(":", 1)[1]
    if lang not in ("uz", "ru"):
        lang = "uz"
    await db.set_language(call.from_user.id, lang)
    await call.message.edit_text(t("language_set", lang))

    # Telefon raqam so'raymiz (faqat tugma orqali)
    await state.set_state(Registration.phone)
    await call.message.answer(
        t("ask_phone", lang), reply_markup=phone_request_kb(lang)
    )
    await call.answer()


@router.message(Registration.phone, F.contact)
async def receive_phone(message: Message, state: FSMContext) -> None:
    contact = message.contact
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"

    # Faqat O'ZINING raqamini yuborishi majburiy
    if contact.user_id != message.from_user.id:
        await message.answer(
            t("phone_not_own", lang), reply_markup=phone_request_kb(lang)
        )
        return

    phone = contact.phone_number
    user = await db.complete_registration(message.from_user.id, phone)
    first_time = getattr(user, "_first_time", True) if user else True

    await state.clear()
    await message.answer(t("registration_done", lang), reply_markup=remove_kb)

    # Referal 'join' bonusini egasiga beramiz (faqat birinchi marta)
    if first_time:
        inviter_id = await db.grant_referral_join_bonus(message.from_user.id)
        if inviter_id is not None:
            inviter = await db.get_user(inviter_id)
            inv_lang = (inviter.language if inviter else "uz") or "uz"
            try:
                await message.bot.send_message(
                    inviter_id,
                    t(
                        "referral_join_notify",
                        inv_lang,
                        amount=config.referral_join_bonus,
                    ),
                )
            except Exception:
                pass

    # Asosiy menyu
    await message.answer(
        t("main_menu", lang),
        reply_markup=main_menu_kb(lang, config.is_admin(message.from_user.id)),
    )


@router.message(Registration.phone)
async def reject_manual_phone(message: Message) -> None:
    """Qo'lda yozilgan har qanday matn/raqam rad etiladi."""
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    await message.answer(
        t("phone_manual_rejected", lang), reply_markup=phone_request_kb(lang)
    )
