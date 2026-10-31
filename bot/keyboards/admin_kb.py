"""Admin panel klaviaturalari (inline)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_kb(is_owner: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
        [
            InlineKeyboardButton(text="🎯 Vazifalar", callback_data="adm:tasks"),
            InlineKeyboardButton(text="📢 Majburiy obuna", callback_data="adm:channels"),
        ],
        [
            InlineKeyboardButton(text="🎁 Promokodlar", callback_data="adm:promos"),
            InlineKeyboardButton(text="👥 Referallar", callback_data="adm:refs"),
        ],
        [
            InlineKeyboardButton(text="💰 Balans qo'shish", callback_data="adm:balance"),
            InlineKeyboardButton(text="🚫 Ban / Unban", callback_data="adm:ban"),
        ],
        [
            InlineKeyboardButton(text="📣 Broadcast", callback_data="adm:broadcast"),
            InlineKeyboardButton(text="💾 Backup", callback_data="adm:backup"),
        ],
        [InlineKeyboardButton(text="💳 To'lov sozlamalari", callback_data="adm:pay")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="adm:close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def backup_admin_kb(channel_connected: bool) -> InlineKeyboardMarkup:
    rows = []
    if channel_connected:
        rows.append(
            [InlineKeyboardButton(
                text="🔄 Kanalni o'zgartirish", callback_data="adm:bk_setchannel"
            )]
        )
        rows.append(
            [InlineKeyboardButton(
                text="🗑 Kanalni uzish", callback_data="adm:bk_unsetchannel"
            )]
        )
        rows.append(
            [InlineKeyboardButton(
                text="📥 Foydalanuvchilar fayli", callback_data="adm:bk_users"
            )]
        )
        rows.append(
            [InlineKeyboardButton(
                text="📥 Balanslar fayli", callback_data="adm:bk_balance"
            )]
        )
        rows.append(
            [InlineKeyboardButton(
                text="🗄 To'liq backup (.db)", callback_data="adm:bk_full"
            )]
        )
    else:
        rows.append(
            [InlineKeyboardButton(
                text="📢 Kanalni ulash", callback_data="adm:bk_setchannel"
            )]
        )
    rows.append(
        [InlineKeyboardButton(text="⬅️ Admin menyu", callback_data="adm:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Admin menyu", callback_data="adm:home")]
        ]
    )


def tasks_admin_kb(tasks: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Vazifa qo'shish", callback_data="adm:task_add")]
    ]
    for task in tasks:
        title = task.channel_title or task.channel_id
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📢 {title} ({task.reward:,} so'm)",
                    callback_data="noop",
                ),
                InlineKeyboardButton(
                    text="🗑", callback_data=f"adm:task_del:{task.id}"
                ),
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="⬅️ Admin menyu", callback_data="adm:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channels_admin_kb(channels: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="adm:ch_add")]
    ]
    for ch in channels:
        title = ch.channel_title or ch.channel_id
        rows.append(
            [
                InlineKeyboardButton(text=f"📢 {title}", callback_data="noop"),
                InlineKeyboardButton(
                    text="🗑", callback_data=f"adm:ch_del:{ch.id}"
                ),
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="⬅️ Admin menyu", callback_data="adm:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def promos_admin_kb(promos: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Promokod yaratish", callback_data="adm:promo_add")]
    ]
    for p in promos[:20]:
        limit = "∞" if p.max_uses == 0 else str(p.max_uses)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🎁 {p.code} — {p.reward:,} so'm ({p.used_count}/{limit})",
                    callback_data="noop",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="⬅️ Admin menyu", callback_data="adm:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ------------------------------------------------------------------ #
#  To'lov sozlamalari
# ------------------------------------------------------------------ #
def payment_main_kb(payme_on: bool, click_on: bool, card_on: bool) -> InlineKeyboardMarkup:
    def mark(on: bool) -> str:
        return "🟢" if on else "🔴"

    rows = [
        [InlineKeyboardButton(
            text=f"{mark(payme_on)} Payme", callback_data="adm:pay_payme"
        )],
        [InlineKeyboardButton(
            text=f"{mark(click_on)} Click", callback_data="adm:pay_click"
        )],
        [InlineKeyboardButton(
            text=f"{mark(card_on)} Karta (avto)", callback_data="adm:pay_card"
        )],
        [InlineKeyboardButton(text="⬅️ Admin menyu", callback_data="adm:home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payme_settings_kb(enabled: bool) -> InlineKeyboardMarkup:
    toggle = "🔴 O'chirish" if enabled else "🟢 Yoqish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="adm:pay_toggle:payme")],
        [InlineKeyboardButton(text="✏️ Merchant ID", callback_data="adm:pay_set:pay_payme_merchant_id")],
        [InlineKeyboardButton(text="✏️ Secret key", callback_data="adm:pay_set:pay_payme_key")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:pay")],
    ])


def click_settings_kb(enabled: bool) -> InlineKeyboardMarkup:
    toggle = "🔴 O'chirish" if enabled else "🟢 Yoqish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="adm:pay_toggle:click")],
        [InlineKeyboardButton(text="✏️ Service ID", callback_data="adm:pay_set:pay_click_service_id")],
        [InlineKeyboardButton(text="✏️ Merchant ID", callback_data="adm:pay_set:pay_click_merchant_id")],
        [InlineKeyboardButton(text="✏️ Secret key", callback_data="adm:pay_set:pay_click_key")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:pay")],
    ])


def card_settings_kb(enabled: bool) -> InlineKeyboardMarkup:
    toggle = "🔴 O'chirish" if enabled else "🟢 Yoqish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="adm:pay_toggle:card")],
        [InlineKeyboardButton(text="✏️ Karta raqami", callback_data="adm:pay_set:pay_card_number")],
        [InlineKeyboardButton(text="✏️ Karta egasi", callback_data="adm:pay_set:pay_card_holder")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:pay")],
    ])
