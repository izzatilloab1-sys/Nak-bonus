"""Kanal nazorati:
  - Bot kanalга admin qilinganда avtomatik invite link yaratish
  - Bot linki orqali qo'shilgan/chiqib ketganlarni real vaqtda hisoblash
  - Chegaraga (sub_limit) yetganda admin'ga xabar
  - Chiqib ketganlarda zadaniya bonusini qaytarish (ikkala tomondan)

Telegram update'lari:
  - my_chat_member : botning kanaldagi roli o'zgarganda (admin bo'ldi/bo'lmadi)
  - chat_member    : kanalga a'zo qo'shilganda/chiqqanda (bot admin bo'lsa keladi)
"""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import ChatMemberUpdated

from bot.config import config
from bot.database import db

logger = logging.getLogger("bot.channel_tracker")

router = Router(name="channel_tracker")

_JOINED = {"member", "administrator", "creator", "restricted"}
_LEFT = {"left", "kicked"}


# ------------------------------------------------------------------ #
#  Botning kanaldagi roli o'zgarganda → admin bo'lsa invite link yaratamiz
# ------------------------------------------------------------------ #
@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, bot: Bot) -> None:
    new_status = event.new_chat_member.status
    chat = event.chat
    # Faqat kanal/supergruppada ishlaymiz
    if chat.type not in ("channel", "supergroup", "group"):
        return

    if new_status in ("administrator", "creator"):
        # Bot admin bo'ldi — shu kanal DB'da zadaniya/majburiy sifatida bormi?
        entities = await db.find_channel_entities(chat.id)
        if not entities["tasks"] and not entities["channels"]:
            # DB'da yo'q — e'tibor bermaymiz (admin keyin qo'shishi mumkin)
            logger.info("Bot %s (%s) ga admin bo'ldi, lekin DB'da yo'q", chat.title, chat.id)
            return
        await _ensure_invite_link(bot, chat.id)


async def _ensure_invite_link(bot: Bot, chat_id) -> str | None:
    """Kanal uchun invite link bo'lmasa — bot yaratadi va DB'ga yozadi."""
    existing = await db.find_channel_entities(chat_id)
    all_rows = existing["tasks"] + existing["channels"]
    # Birortasida link bo'lsa — qayta yaratmaymiz
    for row in all_rows:
        if row.invite_link:
            return row.invite_link
    try:
        link = await bot.create_chat_invite_link(
            chat_id=chat_id,
            name="Bot orqali (hisob uchun)",
            creates_join_request=False,
        )
        await db.set_channel_invite_link(chat_id, link.invite_link)
        logger.info("Kanal %s uchun invite link yaratildi", chat_id)
        return link.invite_link
    except Exception as e:
        logger.warning("Invite link yaratilmadi (%s): %s", chat_id, e)
        return None


# ------------------------------------------------------------------ #
#  Kanalga a'zo qo'shilganda / chiqqanda
# ------------------------------------------------------------------ #
@router.chat_member()
async def on_chat_member(event: ChatMemberUpdated, bot: Bot) -> None:
    chat = event.chat
    user = event.new_chat_member.user
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    # Bot orqali (invite_link) kelgan bo'lsa — event.invite_link bo'ladi
    via_link = event.invite_link.invite_link if event.invite_link else None

    joined = old_status in _LEFT and new_status in _JOINED
    left = old_status in _JOINED and new_status in _LEFT

    if joined:
        notify = await db.increment_joined(chat.id, via_link)
        for n in notify:
            await _notify_limit_reached(bot, n)
        # Chiqib ketgan (revoked) bonus bor bo'lsa — qayta qo'shilganiga ko'ra
        # tiklashni "✅ Tekshirish" bosganda qilamiz (tasks.py). Bu yerda faqat
        # hisoblaymiz.

    elif left:
        await db.increment_left(chat.id, via_link)
        await _handle_user_left(bot, chat.id, user.id)


# ------------------------------------------------------------------ #
#  Foydalanuvchi chiqib ketdi → bonusni qaytarish + egaga xabar
# ------------------------------------------------------------------ #
async def _handle_user_left(bot: Bot, chat_id, user_id: int) -> None:
    """Chiqib ketgan odamning shu kanaldagi zadaniya bonusini (1 hafta ichida
    bo'lsa) ikkala tomondan qaytaradi va egaga xabar yuboradi."""
    entities = await db.find_channel_entities(chat_id)
    for task in entities["tasks"]:
        result = await db.revoke_task_bonus(task.id, user_id)
        if result is None:
            continue  # bonus faol emas / 1 hafta o'tgan / yo'q
        await _notify_bonus_revoked(bot, user_id, task, result)


async def _notify_bonus_revoked(bot: Bot, user_id: int, task, result: dict) -> None:
    # Chiqib ketgan foydalanuvchiga xabar
    user = await db.get_user(user_id)
    lang = (user.language if user else "uz") or "uz"
    title = task.channel_title or task.channel_id
    try:
        if lang == "ru":
            txt = (
                f"⚠️ Вы покинули канал «{title}».\n"
                f"Бонус за это задание отменён: <b>-{result['reward']:,} сум</b>.\n"
                f"Вернитесь и нажмите «✅ Проверить», чтобы вернуть бонус."
            )
        else:
            txt = (
                f"⚠️ Siz «{title}» kanalidan chiqib ketdingiz.\n"
                f"Shu vazifa bonusi bekor qilindi: <b>-{result['reward']:,} so'm</b>.\n"
                f"Qaytib qo'shilib «✅ Tekshirish» bossangiz, bonus qaytadi."
            )
        await bot.send_message(user_id, txt)
    except Exception:
        pass

    # Referal egasiga xabar (ID + username bilan)
    inviter_id = result.get("inviter_id")
    inviter_bonus = result.get("inviter_bonus", 0)
    if inviter_id and inviter_bonus > 0:
        inviter = await db.get_user(inviter_id)
        inv_lang = (inviter.language if inviter else "uz") or "uz"
        uname = f"@{user.username}" if user and user.username else "—"
        try:
            if inv_lang == "ru":
                txt = (
                    f"⚠️ Ваш реферал выполнил задание и покинул канал.\n"
                    f"👤 ID: <code>{user_id}</code>\n"
                    f"🔗 Username: {uname}\n"
                    f"📢 Канал: {title}\n"
                    f"Реферальный бонус отменён: <b>-{inviter_bonus:,} сум</b>."
                )
            else:
                txt = (
                    f"⚠️ Sizning referalingiz vazifani bajarib kanaldan chiqib ketdi.\n"
                    f"👤 ID: <code>{user_id}</code>\n"
                    f"🔗 Username: {uname}\n"
                    f"📢 Kanal: {title}\n"
                    f"Referal bonusi bekor qilindi: <b>-{inviter_bonus:,} so'm</b>."
                )
            await bot.send_message(inviter_id, txt)
        except Exception:
            pass


# ------------------------------------------------------------------ #
#  Chegaraga yetganda admin'ga xabar
# ------------------------------------------------------------------ #
async def _notify_limit_reached(bot: Bot, info: dict) -> None:
    kind_uz = "zadaniya" if info["kind"] == "task" else "majburiy obuna"
    text = (
        f"🎯 <b>Chegaraga yetildi!</b>\n\n"
        f"📢 Kanal: {info['title']}\n"
        f"🔖 Turi: {kind_uz}\n"
        f"🎚 Chegara: <b>{info['limit']:,}</b>\n"
        f"✅ Bot orqali kirgan: <b>{info['joined']:,}</b>\n"
        f"🚪 Chiqib ketgan: <b>{info['left']:,}</b>\n"
        f"👥 Hozir faol: <b>{info['active']:,}</b>\n\n"
        f"ℹ️ Kanal avtomatik o'chirilmadi — o'zingiz qaror qiling."
    )
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass
