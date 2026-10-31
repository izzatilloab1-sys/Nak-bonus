"""Kanal obunasini tekshirish (majburiy obuna va vazifalar uchun)."""
from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# Obuna hisoblanadigan statuslar
_SUBSCRIBED_STATUSES = {"member", "administrator", "creator", "restricted"}


async def is_subscribed(bot: Bot, channel_id: str, user_id: int) -> bool:
    """Foydalanuvchi kanalga obuna bo'lganini tekshiradi.
    channel_id: '-100...' yoki '@username'.
    Bot kanalda admin bo'lishi kerak."""
    chat_id: str | int = channel_id
    if isinstance(channel_id, str) and channel_id.lstrip("-").isdigit():
        chat_id = int(channel_id)
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in _SUBSCRIBED_STATUSES
    except (TelegramBadRequest, TelegramForbiddenError):
        # Bot kanalda admin emas yoki kanal topilmadi — tekshirib bo'lmaydi
        return False
    except Exception:
        return False


async def check_all_required(bot: Bot, channels: list, user_id: int) -> list:
    """Obuna bo'linmagan majburiy kanallar ro'yxatini qaytaradi."""
    not_subscribed = []
    for ch in channels:
        if not await is_subscribed(bot, ch.channel_id, user_id):
            not_subscribed.append(ch)
    return not_subscribed
