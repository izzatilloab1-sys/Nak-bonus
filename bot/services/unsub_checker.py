"""Davriy chiqib ketish tekshiruvi (zaxira mexanizm).

chat_member update real vaqtda ishlaydi, lekin ba'zan o'tkazib yuborilishi
mumkin (bot vaqtincha offline, update yo'qolgan, bot kanaldan olingan va h.k.).
Shuning uchun har N soatda barcha FAOL bonusli zadaniya bajarishlarni qayta
tekshiramiz: foydalanuvchi hali obunami? Agar chiqib ketgan bo'lsa — bonus
ikkala tomondan qaytariladi va egaga xabar beriladi.

Faqat bajarilganiga `unsub_check_days` (1 hafta) dan kam vaqt o'tganlarni
tekshiramiz — undan keyin bonus "qotadi" (qaytarilmaydi).
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from bot.config import config
from bot.database import db
from bot.services.channel_tracker import _notify_bonus_revoked
from bot.services.subscription import is_subscribed

logger = logging.getLogger("bot.unsub_checker")


async def run_unsub_check(bot: Bot) -> int:
    """Bir marta to'liq tekshiruv. Qaytaradi: nechta bonus qaytarildi."""
    completions = await db.get_active_completions_within(config.unsub_check_days)
    revoked_count = 0
    for item in completions:
        task_id = item["task_id"]
        user_id = item["user_id"]
        task = await db.get_task(task_id)
        if task is None or not task.is_active:
            continue
        try:
            still = await is_subscribed(bot, task.channel_id, user_id)
        except Exception:
            # Tekshirib bo'lmasa (bot admin emas va h.k.) — tegmaymiz
            continue
        if not still:
            result = await db.revoke_task_bonus(task_id, user_id)
            if result is not None:
                await _notify_bonus_revoked(bot, user_id, task, result)
                revoked_count += 1
        # Telegram limitidan himoya
        await asyncio.sleep(0.1)
    if revoked_count:
        logger.info("Davriy tekshiruv: %d ta bonus qaytarildi", revoked_count)
    return revoked_count


async def unsub_scheduler(bot: Bot, interval_hours: int = 6) -> None:
    """Har `interval_hours` soatda chiqib ketganlarni tekshiradi."""
    logger.info("Chiqib ketish tekshiruvi scheduleri ishga tushdi (har %d soat).",
                interval_hours)
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
        except asyncio.CancelledError:
            logger.info("Unsub scheduler to'xtatildi.")
            raise
        try:
            await run_unsub_check(bot)
        except Exception as e:
            logger.error("Unsub tekshiruvi xatosi: %s", e)
