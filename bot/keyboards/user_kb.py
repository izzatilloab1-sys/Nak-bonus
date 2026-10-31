"""Foydalanuvchi klaviaturalari."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.utils.texts import t

remove_kb = ReplyKeyboardRemove()


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            ]
        ]
    )


def phone_request_kb(lang: str) -> ReplyKeyboardMarkup:
    """Faqat 'telefon raqamni yuborish' tugmasi (request_contact)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("phone_button", lang), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_kb(lang: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=t("btn_balance", lang)),
         KeyboardButton(text=t("btn_tasks", lang))],
        [KeyboardButton(text=t("btn_referral", lang)),
         KeyboardButton(text=t("btn_promo", lang))],
        [KeyboardButton(text=t("btn_topup", lang)),
         KeyboardButton(text=t("btn_language", lang))],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=t("btn_admin", lang))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def subscription_kb(channels: list, lang: str) -> InlineKeyboardMarkup:
    """Majburiy obuna: kanal tugmalari + tekshirish."""
    rows = []
    for ch in channels:
        url = ch.channel_url or (
            f"https://t.me/{ch.channel_id.lstrip('@')}"
            if ch.channel_id.startswith("@")
            else None
        )
        title = ch.channel_title or ch.channel_id
        if url:
            rows.append([InlineKeyboardButton(text=f"📢 {title}", url=url)])
    rows.append(
        [InlineKeyboardButton(
            text=t("check_subscription", lang), callback_data="check_sub"
        )]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def task_kb(task, completed: bool, lang: str) -> InlineKeyboardMarkup:
    rows = []
    url = task.channel_url or (
        f"https://t.me/{task.channel_id.lstrip('@')}"
        if task.channel_id.startswith("@")
        else None
    )
    if url:
        rows.append([InlineKeyboardButton(text=t("btn_task_open", lang), url=url)])
    if not completed:
        rows.append(
            [InlineKeyboardButton(
                text=t("btn_task_check", lang),
                callback_data=f"task_check:{task.id}",
            )]
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="✅", callback_data="noop")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topup_amounts_kb(lang: str) -> InlineKeyboardMarkup:
    amounts = [5000, 10000, 20000, 50000, 100000, 200000]
    rows = []
    for i in range(0, len(amounts), 2):
        row = [
            InlineKeyboardButton(
                text=f"{a:,} so'm".replace(",", " "),
                callback_data=f"topup:{a}",
            )
            for a in amounts[i:i + 2]
        ]
        rows.append(row)
    rows.append(
        [InlineKeyboardButton(text=t("topup_custom", lang), callback_data="topup:custom")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pay_link_kb(url: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("topup_pay_button", lang), url=url)]
        ]
    )
