"""Zaxira (backup) servisi.

3 xil zaxira:
  1. users   — foydalanuvchi ma'lumotlari (id, username, telefon, ism, til, sana) → CSV
  2. balance — id bo'yicha balanslar (id, username, balans) → CSV
  3. full    — butun SQLite bazasi (.db fayli) — ipidan ignasigacha hamma ma'lumot

Barcha fayllar admin ulagan Telegram KANALGA yuboriladi (send_document).
Kanal ID DB'dagi `settings` jadvalida `backup_channel_id` kalitida saqlanadi.

Har kuni `users` va `balance` avtomatik yuboriladi (main.py'dagi scheduler).
Uchalasi ham admin paneldan qo'lda yuborilishi mumkin.
"""
from __future__ import annotations

import csv
import io
import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

from aiogram import Bot
from aiogram.types import BufferedInputFile, FSInputFile
from sqlalchemy import select

from bot.config import config
from bot.database import db
from bot.database.models import User

logger = logging.getLogger("bot.backup")

BACKUP_CHANNEL_KEY = "backup_channel_id"


# ------------------------------------------------------------------ #
#  Kanal sozlamasi
# ------------------------------------------------------------------ #
async def get_backup_channel() -> str | None:
    return await db.get_setting(BACKUP_CHANNEL_KEY)


async def set_backup_channel(channel_id: str | None) -> None:
    await db.set_setting(BACKUP_CHANNEL_KEY, channel_id)


def _resolve_chat_id(channel_id: str) -> str | int:
    """'-100...' bo'lsa int, '@username' bo'lsa string."""
    if isinstance(channel_id, str) and channel_id.lstrip("-").isdigit():
        return int(channel_id)
    return channel_id


# ------------------------------------------------------------------ #
#  CSV generatsiya
# ------------------------------------------------------------------ #
async def _build_users_csv() -> bytes:
    """Foydalanuvchi ma'lumotlari: id, username, telefon, ism, til, sana."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "username", "telefon", "ism", "til", "royxatdan_otgan"]
    )
    async with db.async_session() as session:
        rows = await session.execute(select(User).order_by(User.id))
        users = list(rows.scalars().all())
    for u in users:
        writer.writerow(
            [
                u.id,
                u.username or "",
                u.phone or "",
                u.full_name or "",
                u.language or "",
                u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
            ]
        )
    # Excel UTF-8 BOM bilan to'g'ri ochilsin
    return ("\ufeff" + output.getvalue()).encode("utf-8")


async def _build_balance_csv() -> bytes:
    """Balanslar: id, username, balans (so'm)."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "username", "balans_som"])
    async with db.async_session() as session:
        rows = await session.execute(
            select(User.id, User.username, User.balance).order_by(
                User.balance.desc()
            )
        )
        data = rows.all()
    for uid, uname, bal in data:
        writer.writerow([uid, uname or "", bal])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


# ------------------------------------------------------------------ #
#  To'liq DB nusxasi (xavfsiz)
# ------------------------------------------------------------------ #
def _make_db_snapshot() -> str | None:
    """SQLite bazasining xavfsiz nusxasini yaratadi (VACUUM INTO — ochiq
    baza buzilmaydi). Vaqtinchalik fayl yo'lini qaytaradi."""
    src = config.sqlite_path
    if not src or not os.path.exists(src):
        return None
    tmp_dir = tempfile.gettempdir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(tmp_dir, f"backup_{stamp}.db")
    try:
        # VACUUM INTO — eng xavfsiz usul (WAL va ochiq ulanishlarni hisobga oladi)
        conn = sqlite3.connect(src)
        try:
            conn.execute("VACUUM INTO ?", (dest,))
        finally:
            conn.close()
    except Exception as e:
        logger.warning("VACUUM INTO ishlamadi (%s), oddiy copy bilan urinamiz", e)
        try:
            shutil.copy2(src, dest)
        except Exception as e2:
            logger.error("DB nusxa olishda xato: %s", e2)
            return None
    return dest


# ------------------------------------------------------------------ #
#  Yuborish funksiyalari
# ------------------------------------------------------------------ #
async def send_users_backup(bot: Bot, channel_id: str | None = None) -> bool:
    channel_id = channel_id or await get_backup_channel()
    if not channel_id:
        return False
    data = await _build_users_csv()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    fname = f"users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    file = BufferedInputFile(data, filename=fname)
    try:
        await bot.send_document(
            _resolve_chat_id(channel_id),
            file,
            caption=f"👥 Foydalanuvchilar ma'lumoti\n🗓 {stamp}",
        )
        return True
    except Exception as e:
        logger.error("users backup yuborilmadi: %s", e)
        return False


async def send_balance_backup(bot: Bot, channel_id: str | None = None) -> bool:
    channel_id = channel_id or await get_backup_channel()
    if not channel_id:
        return False
    data = await _build_balance_csv()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    fname = f"balance_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    file = BufferedInputFile(data, filename=fname)
    try:
        await bot.send_document(
            _resolve_chat_id(channel_id),
            file,
            caption=f"💰 Balanslar (id bo'yicha)\n🗓 {stamp}",
        )
        return True
    except Exception as e:
        logger.error("balance backup yuborilmadi: %s", e)
        return False


async def send_full_backup(bot: Bot, channel_id: str | None = None) -> bool:
    channel_id = channel_id or await get_backup_channel()
    if not channel_id:
        return False
    snapshot = _make_db_snapshot()
    if snapshot is None:
        logger.error("To'liq backup: DB fayli topilmadi")
        return False
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        file = FSInputFile(
            snapshot,
            filename=f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
        )
        await bot.send_document(
            _resolve_chat_id(channel_id),
            file,
            caption=(
                "🗄 <b>To'liq zaxira (hamma ma'lumot)</b>\n"
                f"🗓 {stamp}\n\n"
                "Tiklash: shu faylni server'da bonus_bot.db o'rniga qo'ying."
            ),
        )
        return True
    except Exception as e:
        logger.error("full backup yuborilmadi: %s", e)
        return False
    finally:
        try:
            os.remove(snapshot)
        except OSError:
            pass


async def send_daily_backup(bot: Bot) -> None:
    """Har kunlik avtomatik backup: users + balance."""
    channel_id = await get_backup_channel()
    if not channel_id:
        logger.info("Backup kanali ulanmagan — avtomatik backup o'tkazib yuborildi")
        return
    await send_users_backup(bot, channel_id)
    await send_balance_backup(bot, channel_id)
    logger.info("Kunlik backup yuborildi (users + balance)")
