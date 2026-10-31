"""Admin panel: statistika, vazifa/kanal/promokod, balans, ban, broadcast."""
from __future__ import annotations

import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.keyboards.admin_kb import (
    admin_main_kb,
    back_to_admin_kb,
    backup_admin_kb,
    card_settings_kb,
    channels_admin_kb,
    click_settings_kb,
    payment_main_kb,
    payme_settings_kb,
    promos_admin_kb,
    tasks_admin_kb,
)
from bot.services import backup as backup_service
from bot.services import payment_settings
from bot.utils.states import (
    AdminAddChannel,
    AdminAddTask,
    AdminBackupChannel,
    AdminBalance,
    AdminBan,
    AdminBroadcast,
    AdminCreatePromo,
    AdminPayment,
    AdminRefLookup,
)

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return config.is_admin(user_id)


# ------------------------------------------------------------------ #
#  Admin panelga kirish
# ------------------------------------------------------------------ #
@router.message(Command("admin"))
@router.message(F.text.in_({"🛠 Admin panel", "🛠 Админ панель"}))
async def admin_entry(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🛠 <b>Admin panel</b>\nKerakli bo'limni tanlang:",
        reply_markup=admin_main_kb(is_owner=(message.from_user.id == config.owner_id)),
    )


@router.callback_query(F.data == "adm:home")
async def admin_home(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.clear()
    await call.message.edit_text(
        "🛠 <b>Admin panel</b>\nKerakli bo'limni tanlang:",
        reply_markup=admin_main_kb(is_owner=(call.from_user.id == config.owner_id)),
    )
    await call.answer()


@router.callback_query(F.data == "adm:close")
async def admin_close(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    await call.message.delete()
    await call.answer()


# ------------------------------------------------------------------ #
#  Statistika
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:stats")
async def admin_stats(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    s = await db.get_stats()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{s['total_users']}</b>\n"
        f"✅ Ro'yxatdan o'tgan: <b>{s['registered']}</b>\n"
        f"🚫 Banlangan: <b>{s['banned']}</b>\n\n"
        f"💰 Umumiy balans (barcha): <b>{s['total_balance']:,} so'm</b>\n"
        f"💳 To'langan buyurtmalar: <b>{s['paid_orders']}</b>\n"
        f"💵 Jami to'lovlar: <b>{s['total_paid']:,} so'm</b>"
    )
    await call.message.edit_text(text, reply_markup=back_to_admin_kb())
    await call.answer()


# ------------------------------------------------------------------ #
#  Vazifalar (tasks)
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:tasks")
async def admin_tasks(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    tasks = await db.get_active_tasks()
    lines = ["🎯 <b>Vazifalar</b>\nKanalga obuna → so'm mukofot.\n"]
    for tk in tasks:
        title = tk.channel_title or tk.channel_id
        limit_txt = "∞" if tk.sub_limit == 0 else f"{tk.sub_limit:,}"
        active = max(0, tk.joined_count - tk.left_count)
        lines.append(
            f"\n📢 <b>{title}</b> — {tk.reward:,} so'm\n"
            f"   ✅ Bot orqali kirgan: {tk.joined_count:,} | "
            f"🚪 chiqgan: {tk.left_count:,} | 👥 faol: {active:,} | "
            f"🎚 chegara: {limit_txt}"
        )
    if len(tasks) == 0:
        lines.append("\nHali vazifa yo'q.")
    lines.append(
        "\n\n⚠️ Obuna tekshiruvi va hisob uchun bot kanalда <b>admin</b> bo'lsin."
    )
    await call.message.edit_text(
        "".join(lines), reply_markup=tasks_admin_kb(tasks)
    )
    await call.answer()


@router.callback_query(F.data == "adm:task_add")
async def admin_task_add(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminAddTask.channel)
    await call.message.edit_text(
        "📢 Kanal ID yoki @username kiriting:\n"
        "(masalan: <code>@mychannel</code> yoki <code>-1001234567890</code>)\n\n"
        "⚠️ Bot shu kanalda admin bo'lishi shart.",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminAddTask.channel, F.text)
async def admin_task_channel(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(channel=message.text.strip())
    await state.set_state(AdminAddTask.url)
    await message.answer(
        "🔗 Kanal havolasini kiriting (yoki '-' agar @username bo'lsa):\n"
        "(masalan: <code>https://t.me/mychannel</code>)"
    )


@router.message(AdminAddTask.url, F.text)
async def admin_task_url(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    url = message.text.strip()
    await state.update_data(url=None if url == "-" else url)
    await state.set_state(AdminAddTask.reward)
    await message.answer("💵 Mukofot summasini so'mda kiriting (masalan 500):")


@router.message(AdminAddTask.reward, F.text)
async def admin_task_reward(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer("❌ Faqat raqam kiriting. Qaytadan:")
        return
    await state.update_data(reward=int(raw))
    await state.set_state(AdminAddTask.limit)
    await message.answer(
        "🎚 Obunachi chegarasini kiriting (0 = cheksiz):\n"
        "Bot orqali shu songa yetganda sizga xabar keladi.\n"
        "(bu — bot invite linki orqali kirganlar soni)"
    )


@router.message(AdminAddTask.limit, F.text)
async def admin_task_limit(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer("❌ Faqat raqam kiriting (0 = cheksiz). Qaytadan:")
        return
    sub_limit = int(raw)
    data = await state.get_data()
    channel = data["channel"]
    url = data.get("url")
    reward = data["reward"]

    # Kanal sarlavhasini olishga urinamiz (bot admin bo'lsa)
    title = channel
    bot_is_admin = False
    try:
        chat = await bot.get_chat(
            int(channel) if channel.lstrip("-").isdigit() else channel
        )
        title = chat.title or channel
        if not url and chat.username:
            url = f"https://t.me/{chat.username}"
        bot_is_admin = True
    except Exception:
        await message.answer(
            "⚠️ Kanalni tekshirib bo'lmadi (bot admin emas yoki ID noto'g'ri). "
            "Vazifa baribir qo'shiladi, lekin obunani tekshirish va invite link "
            "yaratish uchun botni kanalga admin qiling."
        )

    await db.add_task(channel, title, url, reward, sub_limit=sub_limit)
    await state.clear()

    # Bot admin bo'lsa — darhol invite link yaratamiz (hisob uchun)
    invite_info = ""
    if bot_is_admin:
        try:
            link = await bot.create_chat_invite_link(
                chat_id=int(channel) if channel.lstrip("-").isdigit() else channel,
                name="Bot orqali (hisob uchun)",
            )
            await db.set_channel_invite_link(channel, link.invite_link)
            invite_info = f"\n🔗 Bot linki: {link.invite_link}"
        except Exception:
            invite_info = "\n⚠️ Invite link yaratilmadi (botni admin qiling)."

    limit_txt = "∞" if sub_limit == 0 else f"{sub_limit:,}"
    await message.answer(
        f"✅ Vazifa qo'shildi:\n📢 {title}\n💵 {reward:,} so'm\n"
        f"🎚 Chegara: {limit_txt}{invite_info}"
    )
    tasks = await db.get_active_tasks()
    await message.answer("🎯 <b>Vazifalar</b>:", reply_markup=tasks_admin_kb(tasks))


@router.callback_query(F.data.startswith("adm:task_del:"))
async def admin_task_del(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    task_id = int(call.data.split(":")[-1])
    await db.delete_task(task_id)
    tasks = await db.get_active_tasks()
    await call.message.edit_text(
        "🎯 <b>Vazifalar</b>:", reply_markup=tasks_admin_kb(tasks)
    )
    await call.answer("🗑 O'chirildi")


# ------------------------------------------------------------------ #
#  Majburiy obuna kanallari
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:channels")
async def admin_channels(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    channels = await db.get_required_channels()
    lines = [
        "📢 <b>Majburiy obuna kanallari</b>\n"
        "Foydalanuvchilar botdan foydalanishdan oldin obuna bo'lishi shart.\n"
    ]
    for ch in channels:
        title = ch.channel_title or ch.channel_id
        limit_txt = "∞" if ch.sub_limit == 0 else f"{ch.sub_limit:,}"
        active = max(0, ch.joined_count - ch.left_count)
        lines.append(
            f"\n📢 <b>{title}</b>\n"
            f"   ✅ Bot orqali kirgan: {ch.joined_count:,} | "
            f"🚪 chiqgan: {ch.left_count:,} | 👥 faol: {active:,} | "
            f"🎚 chegara: {limit_txt}"
        )
    if len(channels) == 0:
        lines.append("\nHali kanal yo'q.")
    lines.append("\n\n⚠️ Bot kanalда <b>admin</b> bo'lishi kerak.")
    await call.message.edit_text(
        "".join(lines), reply_markup=channels_admin_kb(channels)
    )
    await call.answer()


@router.callback_query(F.data == "adm:ch_add")
async def admin_ch_add(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminAddChannel.channel)
    await call.message.edit_text(
        "📢 Kanal ID yoki @username kiriting:\n"
        "(masalan: <code>@mychannel</code> yoki <code>-1001234567890</code>)",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminAddChannel.channel, F.text)
async def admin_ch_channel(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(channel=message.text.strip())
    await state.set_state(AdminAddChannel.url)
    await message.answer(
        "🔗 Kanal havolasini kiriting (yoki '-' agar @username bo'lsa):"
    )


@router.message(AdminAddChannel.url, F.text)
async def admin_ch_url(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    url = message.text.strip()
    await state.update_data(url=None if url == "-" else url)
    await state.set_state(AdminAddChannel.limit)
    await message.answer(
        "🎚 Obunachi chegarasini kiriting (0 = cheksiz):\n"
        "Bot orqali shu songa yetganda sizga xabar keladi."
    )


@router.message(AdminAddChannel.limit, F.text)
async def admin_ch_limit(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer("❌ Faqat raqam kiriting (0 = cheksiz). Qaytadan:")
        return
    sub_limit = int(raw)
    data = await state.get_data()
    channel = data["channel"]
    url = data.get("url")

    title = channel
    bot_is_admin = False
    try:
        chat = await bot.get_chat(
            int(channel) if channel.lstrip("-").isdigit() else channel
        )
        title = chat.title or channel
        if not url and chat.username:
            url = f"https://t.me/{chat.username}"
        bot_is_admin = True
    except Exception:
        await message.answer(
            "⚠️ Kanalni tekshirib bo'lmadi. Baribir qo'shiladi, lekin "
            "obunani tekshirish va invite link uchun botni kanalga admin qiling."
        )

    await db.add_required_channel(channel, title, url, sub_limit=sub_limit)
    await state.clear()

    invite_info = ""
    if bot_is_admin:
        try:
            link = await bot.create_chat_invite_link(
                chat_id=int(channel) if channel.lstrip("-").isdigit() else channel,
                name="Bot orqali (hisob uchun)",
            )
            await db.set_channel_invite_link(channel, link.invite_link)
            invite_info = f"\n🔗 Bot linki: {link.invite_link}"
        except Exception:
            invite_info = "\n⚠️ Invite link yaratilmadi (botni admin qiling)."

    limit_txt = "∞" if sub_limit == 0 else f"{sub_limit:,}"
    await message.answer(
        f"✅ Majburiy kanal qo'shildi:\n📢 {title}\n🎚 Chegara: {limit_txt}{invite_info}"
    )
    channels = await db.get_required_channels()
    await message.answer(
        "📢 <b>Majburiy obuna kanallari</b>:",
        reply_markup=channels_admin_kb(channels),
    )


@router.callback_query(F.data.startswith("adm:ch_del:"))
async def admin_ch_del(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    ch_id = int(call.data.split(":")[-1])
    await db.delete_required_channel(ch_id)
    channels = await db.get_required_channels()
    await call.message.edit_text(
        "📢 <b>Majburiy obuna kanallari</b>:",
        reply_markup=channels_admin_kb(channels),
    )
    await call.answer("🗑 O'chirildi")


# ------------------------------------------------------------------ #
#  Promokodlar
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:promos")
async def admin_promos(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    promos = await db.get_all_promocodes()
    await call.message.edit_text(
        "🎁 <b>Promokodlar</b>\nHar akkaunt bir marta ishlatadi.",
        reply_markup=promos_admin_kb(promos),
    )
    await call.answer()


@router.callback_query(F.data == "adm:promo_add")
async def admin_promo_add(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminCreatePromo.code)
    await call.message.edit_text(
        "🎁 Promokod matnini kiriting (masalan: <code>BONUS2026</code>):",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminCreatePromo.code, F.text)
async def admin_promo_code(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(code=message.text.strip())
    await state.set_state(AdminCreatePromo.reward)
    await message.answer("💵 Promokod beradigan so'mni kiriting (masalan 1000):")


@router.message(AdminCreatePromo.reward, F.text)
async def admin_promo_reward(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer("❌ Faqat raqam kiriting. Qaytadan:")
        return
    await state.update_data(reward=int(raw))
    await state.set_state(AdminCreatePromo.max_uses)
    await message.answer(
        "🔢 Nechta marta ishlatilsin? (0 = cheksiz)\n"
        "Masalan 100 — faqat 100 kishi ishlatadi:"
    )


@router.message(AdminCreatePromo.max_uses, F.text)
async def admin_promo_max(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer("❌ Faqat raqam kiriting (0 = cheksiz). Qaytadan:")
        return
    max_uses = int(raw)
    data = await state.get_data()
    promo = await db.create_promocode(data["code"], data["reward"], max_uses)
    await state.clear()

    if promo is None:
        await message.answer("❌ Bu promokod allaqachon mavjud. Boshqa nom tanlang.")
    else:
        limit = "∞" if max_uses == 0 else str(max_uses)
        await message.answer(
            f"✅ Promokod yaratildi:\n"
            f"🎁 <code>{promo.code}</code>\n"
            f"💵 {promo.reward:,} so'm\n"
            f"🔢 Limit: {limit}"
        )
    promos = await db.get_all_promocodes()
    await message.answer(
        "🎁 <b>Promokodlar</b>:", reply_markup=promos_admin_kb(promos)
    )


# ------------------------------------------------------------------ #
#  Referallarni ko'rish
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:refs")
async def admin_refs(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminRefLookup.user_id)
    await call.message.edit_text(
        "👥 Foydalanuvchi ID sini kiriting — u kimlarni taklif qilganini ko'rasiz:",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminRefLookup.user_id, F.text)
async def admin_refs_lookup(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    if not raw.lstrip("-").isdigit():
        await message.answer("❌ Faqat raqamli ID kiriting. Qaytadan:")
        return
    uid = int(raw)
    await state.clear()
    count, refs = await db.get_referral_stats(uid)
    if count == 0:
        await message.answer("ℹ️ Bu foydalanuvchi hech kimni taklif qilmagan.")
    else:
        lines = [f"👥 <b>{count}</b> ta referal:\n"]
        for rid, uname, cnt in refs:
            uname_s = f"@{uname}" if uname else "—"
            lines.append(f"• <code>{rid}</code> ({uname_s}) — {cnt} ta vazifa")
        await message.answer("\n".join(lines))
    await message.answer(
        "🛠 <b>Admin panel</b>:",
        reply_markup=admin_main_kb(is_owner=(message.from_user.id == config.owner_id)),
    )


# ------------------------------------------------------------------ #
#  Balans qo'shish
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:balance")
async def admin_balance(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminBalance.user_id)
    await call.message.edit_text(
        "💰 Balans qo'shmoqchi bo'lgan foydalanuvchi ID sini kiriting:",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminBalance.user_id, F.text)
async def admin_balance_uid(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    if not raw.lstrip("-").isdigit():
        await message.answer("❌ Faqat raqamli ID kiriting. Qaytadan:")
        return
    user = await db.get_user(int(raw))
    if user is None:
        await message.answer("❌ Bunday foydalanuvchi topilmadi. Qaytadan:")
        return
    await state.update_data(user_id=int(raw))
    await state.set_state(AdminBalance.amount)
    await message.answer(
        "💵 Qancha so'm qo'shilsin? (manfiy ham bo'lishi mumkin, masalan -5000):"
    )


@router.message(AdminBalance.amount, F.text)
async def admin_balance_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(" ", "")
    try:
        amount = int(raw)
    except ValueError:
        await message.answer("❌ Faqat butun son kiriting. Qaytadan:")
        return
    data = await state.get_data()
    uid = data["user_id"]
    new_balance = await db.add_balance(uid, amount)
    await state.clear()
    await message.answer(
        f"✅ Bajarildi.\n👤 <code>{uid}</code>\n"
        f"{'➕' if amount >= 0 else '➖'} {abs(amount):,} so'm\n"
        f"💰 Yangi balans: <b>{new_balance:,} so'm</b>"
    )
    # Foydalanuvchiga xabar
    try:
        user = await db.get_user(uid)
        lang = (user.language if user else "uz") or "uz"
        if amount >= 0:
            txt = (
                f"💰 Balansingizga <b>+{amount:,} so'm</b> qo'shildi."
                if lang == "uz"
                else f"💰 На ваш баланс начислено <b>+{amount:,} сум</b>."
            )
        else:
            txt = (
                f"ℹ️ Balansingizdan <b>{abs(amount):,} so'm</b> yechildi."
                if lang == "uz"
                else f"ℹ️ С вашего баланса списано <b>{abs(amount):,} сум</b>."
            )
        await bot.send_message(uid, txt)
    except Exception:
        pass


# ------------------------------------------------------------------ #
#  Ban / Unban
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:ban")
async def admin_ban(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminBan.user_id)
    await call.message.edit_text(
        "🚫 Ban/Unban qilmoqchi bo'lgan foydalanuvchi ID sini kiriting.\n"
        "(Agar banlangan bo'lsa — unban qilinadi, aks holda — banlanadi):",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminBan.user_id, F.text)
async def admin_ban_uid(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    if not raw.lstrip("-").isdigit():
        await message.answer("❌ Faqat raqamli ID kiriting. Qaytadan:")
        return
    uid = int(raw)
    user = await db.get_user(uid)
    if user is None:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
        await state.clear()
        return
    new_state = not user.is_banned
    await db.set_banned(uid, new_state)
    await state.clear()
    if new_state:
        await message.answer(f"🚫 Foydalanuvchi <code>{uid}</code> banlandi.")
    else:
        await message.answer(f"✅ Foydalanuvchi <code>{uid}</code> unban qilindi.")
    await message.answer(
        "🛠 <b>Admin panel</b>:",
        reply_markup=admin_main_kb(is_owner=(message.from_user.id == config.owner_id)),
    )


# ------------------------------------------------------------------ #
#  Broadcast
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminBroadcast.message)
    await call.message.edit_text(
        "📣 Yubormoqchi bo'lgan xabaringizni yuboring "
        "(matn, rasm, va h.k.). Barcha foydalanuvchilarga jo'natiladi:",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminBroadcast.message)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    user_ids = await db.get_all_user_ids()
    await message.answer(f"📣 Yuborilmoqda... ({len(user_ids)} ta foydalanuvchi)")

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # flood limitidan himoya

    await message.answer(
        f"✅ Broadcast yakunlandi.\n"
        f"📤 Yuborildi: <b>{sent}</b>\n"
        f"❌ Yuborilmadi: <b>{failed}</b>"
    )


# ------------------------------------------------------------------ #
#  💾 Backup (zaxira)
# ------------------------------------------------------------------ #
async def _backup_menu_text() -> str:
    channel = await backup_service.get_backup_channel()
    if channel:
        status = f"✅ Ulangan kanal: <code>{channel}</code>"
    else:
        status = "❌ Kanal ulanmagan"
    return (
        "💾 <b>Zaxira (backup)</b>\n\n"
        f"{status}\n\n"
        "• 👥 <b>Foydalanuvchilar fayli</b> — id, username, telefon, ism (CSV)\n"
        "• 💰 <b>Balanslar fayli</b> — id bo'yicha kimda qancha so'm (CSV)\n"
        "• 🗄 <b>To'liq backup</b> — butun baza (.db), hamma ma'lumot\n\n"
        "ℹ️ Foydalanuvchilar va balanslar fayli <b>har kuni avtomatik</b> "
        "kanalga tashlanadi. Shuningdek bu yerdan qo'lda ham olishingiz mumkin."
    )


@router.callback_query(F.data == "adm:backup")
async def admin_backup(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.clear()
    channel = await backup_service.get_backup_channel()
    await call.message.edit_text(
        await _backup_menu_text(),
        reply_markup=backup_admin_kb(channel_connected=bool(channel)),
    )
    await call.answer()


@router.callback_query(F.data == "adm:bk_setchannel")
async def admin_bk_setchannel(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.set_state(AdminBackupChannel.channel)
    await call.message.edit_text(
        "📢 Zaxira fayllari yuboriladigan kanal ID yoki @username kiriting:\n"
        "(masalan: <code>-1001234567890</code> yoki <code>@mybackup</code>)\n\n"
        "⚠️ Bot shu kanalda <b>admin</b> bo'lishi shart (fayl yuborish uchun).",
        reply_markup=back_to_admin_kb(),
    )
    await call.answer()


@router.message(AdminBackupChannel.channel, F.text)
async def admin_bk_channel_input(message: Message, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    channel = message.text.strip()
    await state.clear()

    # Botning kanalda fayl yubora olishini tekshiramiz (sinov xabari)
    try:
        chat = await bot.get_chat(
            int(channel) if channel.lstrip("-").isdigit() else channel
        )
        title = chat.title or channel
    except Exception:
        await message.answer(
            "⚠️ Kanalni tekshirib bo'lmadi (bot admin emas yoki ID noto'g'ri).\n"
            "Baribir saqlayapman, lekin botni kanalga <b>admin</b> qilganingizga "
            "ishonch hosil qiling.",
        )
        title = channel

    await backup_service.set_backup_channel(channel)
    await message.answer(
        f"✅ Zaxira kanali ulandi:\n📢 {title}\n<code>{channel}</code>"
    )
    await message.answer(
        await _backup_menu_text(),
        reply_markup=backup_admin_kb(channel_connected=True),
    )


@router.callback_query(F.data == "adm:bk_unsetchannel")
async def admin_bk_unset(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    await backup_service.set_backup_channel(None)
    await call.message.edit_text(
        await _backup_menu_text(),
        reply_markup=backup_admin_kb(channel_connected=False),
    )
    await call.answer("🗑 Kanal uzildi")


@router.callback_query(F.data == "adm:bk_users")
async def admin_bk_users(call: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(call.from_user.id):
        return
    await call.answer("📤 Yuborilmoqda...")
    ok = await backup_service.send_users_backup(bot)
    await call.message.answer(
        "✅ Foydalanuvchilar fayli kanalga yuborildi."
        if ok
        else "❌ Yuborilmadi. Kanal ulanganini va bot admin ekanini tekshiring."
    )


@router.callback_query(F.data == "adm:bk_balance")
async def admin_bk_balance(call: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(call.from_user.id):
        return
    await call.answer("📤 Yuborilmoqda...")
    ok = await backup_service.send_balance_backup(bot)
    await call.message.answer(
        "✅ Balanslar fayli kanalga yuborildi."
        if ok
        else "❌ Yuborilmadi. Kanal ulanganini va bot admin ekanini tekshiring."
    )


@router.callback_query(F.data == "adm:bk_full")
async def admin_bk_full(call: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(call.from_user.id):
        return
    await call.answer("📤 To'liq backup tayyorlanmoqda...")
    ok = await backup_service.send_full_backup(bot)
    await call.message.answer(
        "✅ To'liq backup (.db) kanalga yuborildi."
        if ok
        else "❌ Yuborilmadi. Kanal ulanganini va bot admin ekanini tekshiring."
    )


@router.message(Command("backup"))
async def cmd_backup(message: Message, bot: Bot) -> None:
    """To'liq backup'ni buyruq orqali olish: /backup"""
    if not _is_admin(message.from_user.id):
        return
    channel = await backup_service.get_backup_channel()
    if not channel:
        await message.answer(
            "❌ Avval zaxira kanalini ulang: /admin → 💾 Backup → 📢 Kanalni ulash"
        )
        return
    await message.answer("📤 To'liq backup tayyorlanmoqda...")
    ok = await backup_service.send_full_backup(bot)
    await message.answer(
        "✅ To'liq backup (.db) kanalga yuborildi."
        if ok
        else "❌ Yuborilmadi. Bot kanalда admin ekanini tekshiring."
    )


# ------------------------------------------------------------------ #
#  💳 To'lov sozlamalari (Payme / Click / Karta)
# ------------------------------------------------------------------ #
@router.callback_query(F.data == "adm:pay")
async def admin_pay(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    await state.clear()
    payme_on = await payment_settings.payme_enabled()
    click_on = await payment_settings.click_enabled()
    card_on = await payment_settings.card_enabled()
    await call.message.edit_text(
        "💳 <b>To'lov sozlamalari</b>\n\n"
        "🟢 = yoqilgan, 🔴 = o'chirilgan.\n"
        "Foydalanuvchiga faqat yoqilgan usullar ko'rinadi.\n\n"
        "Har usulni sozlash uchun ustiga bosing:",
        reply_markup=payment_main_kb(payme_on, click_on, card_on),
    )
    await call.answer()


async def _payme_text() -> str:
    on = await payment_settings.payme_enabled()
    mid = await payment_settings.payme_merchant_id()
    key = await payment_settings.payme_key()
    return (
        "💳 <b>Payme</b>\n\n"
        f"Holat: {'🟢 yoqilgan' if on else '🔴 o''chirilgan'}\n"
        f"Merchant ID: <code>{mid or '—'}</code>\n"
        f"Secret key: <code>{'✅ kiritilgan' if key else '—'}</code>\n\n"
        "Payme kabinetida endpoint: <code>https://domen.uz/payme</code>"
    )


async def _click_text() -> str:
    on = await payment_settings.click_enabled()
    sid = await payment_settings.click_service_id()
    mid = await payment_settings.click_merchant_id()
    key = await payment_settings.click_secret_key()
    return (
        "💳 <b>Click</b>\n\n"
        f"Holat: {'🟢 yoqilgan' if on else '🔴 o''chirilgan'}\n"
        f"Service ID: <code>{sid or '—'}</code>\n"
        f"Merchant ID: <code>{mid or '—'}</code>\n"
        f"Secret key: <code>{'✅ kiritilgan' if key else '—'}</code>\n\n"
        "Click kabinetida callback: <code>https://domen.uz/click</code>"
    )


async def _card_text() -> str:
    on = await payment_settings.card_enabled()
    num = await payment_settings.card_number()
    holder = await payment_settings.card_holder()
    return (
        "💵 <b>Karta (avto)</b>\n\n"
        f"Holat: {'🟢 yoqilgan' if on else '🔴 o''chirilgan'}\n"
        f"Karta raqami: <code>{num or '—'}</code>\n"
        f"Karta egasi: <code>{holder or '—'}</code>\n\n"
        "Foydalanuvchi kartaga to'laydi, admin tasdiqlaydi."
    )


@router.callback_query(F.data == "adm:pay_payme")
async def admin_pay_payme(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    on = await payment_settings.payme_enabled()
    await call.message.edit_text(await _payme_text(), reply_markup=payme_settings_kb(on))
    await call.answer()


@router.callback_query(F.data == "adm:pay_click")
async def admin_pay_click(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    on = await payment_settings.click_enabled()
    await call.message.edit_text(await _click_text(), reply_markup=click_settings_kb(on))
    await call.answer()


@router.callback_query(F.data == "adm:pay_card")
async def admin_pay_card(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    on = await payment_settings.card_enabled()
    await call.message.edit_text(await _card_text(), reply_markup=card_settings_kb(on))
    await call.answer()


@router.callback_query(F.data.startswith("adm:pay_toggle:"))
async def admin_pay_toggle(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    method = call.data.split(":")[-1]
    key_map = {
        "payme": ("pay_payme_enabled", payment_settings.payme_enabled, _payme_text, payme_settings_kb),
        "click": ("pay_click_enabled", payment_settings.click_enabled, _click_text, click_settings_kb),
        "card": ("pay_card_enabled", payment_settings.card_enabled, _card_text, card_settings_kb),
    }
    if method not in key_map:
        await call.answer()
        return
    setting_key, is_on_fn, text_fn, kb_fn = key_map[method]
    cur = await is_on_fn()
    await payment_settings.set_value(setting_key, "0" if cur else "1")
    new_on = await is_on_fn()
    await call.message.edit_text(await text_fn(), reply_markup=kb_fn(new_on))
    await call.answer("🟢 Yoqildi" if new_on else "🔴 O'chirildi")


@router.callback_query(F.data.startswith("adm:pay_set:"))
async def admin_pay_set(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return
    setting_key = call.data.split(":", 2)[2]
    await state.set_state(AdminPayment.value)
    await state.update_data(setting_key=setting_key)
    labels = {
        "pay_payme_merchant_id": "Payme Merchant ID",
        "pay_payme_key": "Payme Secret key",
        "pay_click_service_id": "Click Service ID",
        "pay_click_merchant_id": "Click Merchant ID",
        "pay_click_key": "Click Secret key",
        "pay_card_number": "Karta raqami",
        "pay_card_holder": "Karta egasi (ism)",
    }
    label = labels.get(setting_key, "qiymat")
    await call.message.answer(f"✏️ <b>{label}</b> ni kiriting:")
    await call.answer()


@router.message(AdminPayment.value, F.text)
async def admin_pay_set_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    setting_key = data.get("setting_key")
    if not setting_key:
        await state.clear()
        return
    value = message.text.strip()
    await payment_settings.set_value(setting_key, value)
    await state.clear()
    await message.answer("✅ Saqlandi.")
    # Tegishli bo'limga qaytaramiz
    if setting_key.startswith("pay_payme"):
        on = await payment_settings.payme_enabled()
        await message.answer(await _payme_text(), reply_markup=payme_settings_kb(on))
    elif setting_key.startswith("pay_click"):
        on = await payment_settings.click_enabled()
        await message.answer(await _click_text(), reply_markup=click_settings_kb(on))
    elif setting_key.startswith("pay_card"):
        on = await payment_settings.card_enabled()
        await message.answer(await _card_text(), reply_markup=card_settings_kb(on))


# ------------------------------------------------------------------ #
#  Karta to'lovini tasdiqlash / bekor qilish (admin xabaridagi tugmalar)
# ------------------------------------------------------------------ #
@router.callback_query(F.data.startswith("cardok:"))
async def admin_card_confirm(call: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(call.from_user.id):
        return
    order_id = int(call.data.split(":")[-1])
    paid = await db.mark_order_paid(order_id)
    if paid is None:
        await call.answer("Allaqachon to'langan yoki bekor qilingan", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return
    await call.answer("✅ Tasdiqlandi")
    try:
        await call.message.edit_text(
            call.message.html_text + "\n\n✅ <b>Tasdiqlandi</b>"
        )
    except Exception:
        pass
    # Foydalanuvchiga xabar
    user = await db.get_user(paid.user_id)
    lang = (user.language if user else "uz") or "uz"
    try:
        from bot.utils.texts import t as _t
        await bot.send_message(
            paid.user_id, _t("topup_success_notify", lang, amount=paid.amount)
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("cardno:"))
async def admin_card_cancel(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return
    order_id = int(call.data.split(":")[-1])
    await db.cancel_order(order_id)
    await call.answer("❌ Bekor qilindi")
    try:
        await call.message.edit_text(
            call.message.html_text + "\n\n❌ <b>Bekor qilindi</b>"
        )
    except Exception:
        pass
