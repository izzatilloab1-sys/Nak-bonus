"""Vazifalar: reklama kanaliga obuna → so'm mukofot."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database import db
from bot.handlers.user import show_subscription_gate
from bot.keyboards.user_kb import task_kb
from bot.services.subscription import is_subscribed
from bot.utils.texts import t

router = Router(name="tasks")


@router.message(F.text.in_({"🎯 Vazifalar", "🎯 Задания"}))
async def show_tasks(message: Message) -> None:
    user = await db.get_user(message.from_user.id)
    lang = (user.language if user else "uz") or "uz"
    if user is None or not user.is_registered:
        await message.answer(t("not_registered", lang))
        return
    if not await show_subscription_gate(message, lang):
        return

    tasks = await db.get_active_tasks()
    if not tasks:
        await message.answer(t("no_tasks", lang))
        return

    await message.answer(t("tasks_title", lang))
    for task in tasks:
        completed = await db.is_task_completed(task.id, message.from_user.id)
        title = task.channel_title or task.channel_id
        await message.answer(
            t("task_item", lang, title=title, reward=task.reward),
            reply_markup=task_kb(task, completed, lang),
        )


@router.callback_query(F.data.startswith("task_check:"))
async def check_task(call: CallbackQuery) -> None:
    user = await db.get_user(call.from_user.id)
    lang = (user.language if user else "uz") or "uz"

    task_id = int(call.data.split(":", 1)[1])
    task = await db.get_task(task_id)
    if task is None or not task.is_active:
        await call.answer(t("no_tasks", lang), show_alert=True)
        return

    # Allaqachon bajarilganmi?
    if await db.is_task_completed(task_id, call.from_user.id):
        await call.answer(t("task_already_done", lang), show_alert=True)
        return

    # Obunani tekshiramiz
    subscribed = await is_subscribed(call.bot, task.channel_id, call.from_user.id)
    if not subscribed:
        await call.answer(t("task_not_subscribed", lang), show_alert=True)
        return

    # Mukofotni beramiz (atomik)
    reward = await db.complete_task(task_id, call.from_user.id)
    if reward is None:
        await call.answer(t("task_already_done", lang), show_alert=True)
        return

    await call.answer(t("task_reward_given", lang, reward=reward), show_alert=True)
    # Tugmani ✅ ga o'zgartiramiz
    try:
        await call.message.edit_reply_markup(
            reply_markup=task_kb(task, completed=True, lang=lang)
        )
    except Exception:
        pass

    # Referal 'task' bonusi — taklif qilgan odamga
    inviter_id = await db.maybe_grant_referral_task_bonus(call.from_user.id)
    if inviter_id is not None:
        inviter = await db.get_user(inviter_id)
        inv_lang = (inviter.language if inviter else "uz") or "uz"
        try:
            await call.bot.send_message(
                inviter_id,
                t(
                    "referral_task_notify",
                    inv_lang,
                    amount=config.referral_task_bonus,
                ),
            )
        except Exception:
            pass
