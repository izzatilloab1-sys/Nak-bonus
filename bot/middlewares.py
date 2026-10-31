"""Middlewarelar: ban tekshiruvi va foydalanuvchini DB'ga yozish."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from bot.database import db
from bot.utils.texts import t


class BanMiddleware(BaseMiddleware):
    """Banlangan foydalanuvchilarni to'sadi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        db_user = await db.get_user(user.id)
        if db_user is not None and db_user.is_banned:
            lang = db_user.language or "uz"
            if isinstance(event, Update):
                if event.message:
                    await event.message.answer(t("banned", lang))
                elif event.callback_query:
                    await event.callback_query.answer(t("banned", lang), show_alert=True)
            return  # to'xtatamiz

        # DB user obyektini keyingi handlerlarga uzatamiz
        data["db_user"] = db_user
        return await handler(event, data)
