"""Bot kirish nuqtasi.

Polling (Telegram) + Payme webhook serverini BIR process'da ishga tushiradi.

Ishga tushirish:
    python -m bot.main
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from bot.config import config
from bot.database.db import init_db
from bot.handlers import admin, promo, registration, tasks, topup, user
from bot.middlewares import BanMiddleware
from bot.services import backup as backup_service
from bot.services import payme as payme_service
from bot.utils.texts import t
from bot.webhook import build_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("bot.main")


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Middleware
    dp.update.middleware(BanMiddleware())

    # Routerlar — tartib muhim: registratsiya birinchi
    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(tasks.router)
    dp.include_router(promo.router)
    dp.include_router(topup.router)
    dp.include_router(user.router)  # user eng oxirida (umumiy handlerlar)

    return dp


async def _start_payme_webhook() -> web.AppRunner:
    """Payme webhook serverini bot bilan bir event-loop'da ishga tushiradi."""
    app = build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=config.webhook_host, port=config.webhook_port)
    await site.start()
    logger.info(
        "Payme webhook server ishga tushdi: http://%s:%s%s",
        config.webhook_host,
        config.webhook_port,
        config.payme_endpoint_path,
    )
    return runner


async def _daily_backup_scheduler(bot: Bot) -> None:
    """Har kuni bir marta (00:00 server vaqti) users + balance backupini
    kanalga yuboradi. Oddiy, tashqi kutubxonasiz scheduler."""
    import datetime as _dt

    logger.info("Kunlik backup scheduler ishga tushdi.")
    while True:
        now = _dt.datetime.now()
        # Keyingi 00:00 gacha kutamiz
        next_run = (now + _dt.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(
            "Keyingi avtomatik backup: %s (%.0f soatdan keyin)",
            next_run.strftime("%Y-%m-%d %H:%M"),
            sleep_seconds / 3600,
        )
        try:
            await asyncio.sleep(sleep_seconds)
        except asyncio.CancelledError:
            logger.info("Backup scheduler to'xtatildi.")
            raise
        try:
            await backup_service.send_daily_backup(bot)
        except Exception as e:
            logger.error("Kunlik backup xatosi: %s", e)


async def main() -> None:
    if not config.bot_token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. .env faylini to'ldiring (.env.example dan nusxa oling)."
        )

    # DB'ni tayyorlaymiz
    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    # Payme PerformTransaction'dan keyin foydalanuvchiga xabar beradigan funksiya
    async def notify_user_paid(user_id: int, amount_som: int) -> None:
        from bot.database import db

        u = await db.get_user(user_id)
        lang = (u.language if u else "uz") or "uz"
        try:
            await bot.send_message(
                user_id, t("topup_success_notify", lang, amount=amount_som)
            )
        except Exception as e:
            logger.warning("To'lov xabari yuborilmadi (%s): %s", user_id, e)

    payme_service.set_bot_notifier(notify_user_paid)

    # Payme webhook serverini ishga tushiramiz
    runner = await _start_payme_webhook()

    # Kunlik avtomatik backup scheduler (users + balance)
    backup_task = asyncio.create_task(_daily_backup_scheduler(bot))

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot polling boshlandi.")
        await dp.start_polling(bot)
    finally:
        backup_task.cancel()
        try:
            await backup_task
        except asyncio.CancelledError:
            pass
        await runner.cleanup()
        await bot.session.close()
        logger.info("Bot to'xtadi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi (interrupt).")
