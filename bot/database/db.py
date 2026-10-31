"""Ma'lumotlar bazasi bilan ishlash funksiyalari (async SQLAlchemy)."""
from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import config
from bot.database.models import (
    Base,
    Order,
    PromoUse,
    Promocode,
    RequiredChannel,
    Setting,
    Task,
    TaskCompletion,
    Transaction,
    User,
)

engine = create_async_engine(config.db_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ================================================================== #
#  USERS
# ================================================================== #
async def get_user(user_id: int) -> User | None:
    async with async_session() as session:
        return await session.get(User, user_id)


async def create_user_if_absent(
    user_id: int,
    username: str | None,
    full_name: str | None,
    referred_by: int | None = None,
) -> User:
    """Foydalanuvchini yaratadi (agar bo'lmasa). Referalni faqat yangi
    foydalanuvchiga va o'ziga emasligini tekshirib yozadi."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            # Referal firibgarligidan himoya: o'ziga referal bo'lmaydi
            if referred_by == user_id:
                referred_by = None
            # Taklif qiluvchi mavjudligini tekshirish
            if referred_by is not None:
                inviter = await session.get(User, referred_by)
                if inviter is None:
                    referred_by = None
            user = User(
                id=user_id,
                username=username,
                full_name=full_name,
                referred_by=referred_by,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # username/ism yangilanishi mumkin
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if changed:
                await session.commit()
        return user


async def set_language(user_id: int, lang: str) -> None:
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(language=lang)
        )
        await session.commit()


async def complete_registration(user_id: int, phone: str) -> User | None:
    """Telefon raqam tasdiqlangach ro'yxatni yakunlaydi.
    Yangi ro'yxatdan o'tgan bo'lsa (birinchi marta) True qaytaradi."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            return None
        was_registered = user.is_registered
        user.phone = phone
        user.is_registered = True
        await session.commit()
        await session.refresh(user)
        # was_registered=False bo'lsa — endi birinchi marta ro'yxatdan o'tdi
        user._first_time = not was_registered  # type: ignore[attr-defined]
        return user


async def add_balance(user_id: int, amount: int) -> int:
    """Balansga so'm qo'shadi, yangi balansni qaytaradi."""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(
                balance=User.balance + amount
            )
        )
        await session.commit()
        user = await session.get(User, user_id)
        return user.balance if user else 0


async def set_banned(user_id: int, banned: bool) -> bool:
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            return False
        user.is_banned = banned
        await session.commit()
        return True


async def get_all_user_ids() -> list[int]:
    async with async_session() as session:
        rows = await session.execute(select(User.id))
        return [r[0] for r in rows.all()]


async def count_users() -> int:
    async with async_session() as session:
        return (await session.execute(select(func.count(User.id)))).scalar_one()


# ================================================================== #
#  REFERRAL
# ================================================================== #
async def grant_referral_join_bonus(user_id: int) -> int | None:
    """Yangi foydalanuvchi ro'yxatdan o'tganda uning EGASIGA 'join' bonus
    beradi. Egasining ID sini qaytaradi (xabar yuborish uchun) yoki None."""
    if config.referral_join_bonus <= 0:
        return None
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None or user.referred_by is None:
            return None
        inviter = await session.get(User, user.referred_by)
        if inviter is None:
            return None
        inviter.balance += config.referral_join_bonus
        await session.commit()
        return inviter.id


async def maybe_grant_referral_task_bonus(user_id: int) -> int | None:
    """Taklif qilingan foydalanuvchi yetarlicha zadaniya bajargach, uning
    egasiga bir martalik 'task' bonus beradi. Egasining ID sini qaytaradi."""
    if config.referral_task_bonus <= 0:
        return None
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None or user.referred_by is None or user.ref_task_bonus_given:
            return None

        completed = (
            await session.execute(
                select(func.count(TaskCompletion.id)).where(
                    TaskCompletion.user_id == user_id
                )
            )
        ).scalar_one()

        if completed < config.referral_task_threshold:
            return None

        inviter = await session.get(User, user.referred_by)
        if inviter is None:
            user.ref_task_bonus_given = True  # egasi yo'q bo'lsa ham qayta urinmaslik
            await session.commit()
            return None

        inviter.balance += config.referral_task_bonus
        user.ref_task_bonus_given = True
        await session.commit()
        return inviter.id


async def get_referral_stats(user_id: int) -> tuple[int, list[tuple]]:
    """(referallar soni, [(id, username, bajargan zadaniyalar soni)...])"""
    async with async_session() as session:
        refs = (
            await session.execute(
                select(User.id, User.username).where(User.referred_by == user_id)
            )
        ).all()
        result = []
        for rid, uname in refs:
            cnt = (
                await session.execute(
                    select(func.count(TaskCompletion.id)).where(
                        TaskCompletion.user_id == rid
                    )
                )
            ).scalar_one()
            result.append((rid, uname, cnt))
        return len(refs), result


# ================================================================== #
#  TASKS
# ================================================================== #
async def add_task(
    channel_id: str, title: str | None, url: str | None, reward: int
) -> Task:
    async with async_session() as session:
        task = Task(
            channel_id=channel_id,
            channel_title=title,
            channel_url=url,
            reward=reward,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def get_active_tasks() -> list[Task]:
    async with async_session() as session:
        rows = await session.execute(
            select(Task).where(Task.is_active == True).order_by(Task.id)  # noqa: E712
        )
        return list(rows.scalars().all())


async def get_task(task_id: int) -> Task | None:
    async with async_session() as session:
        return await session.get(Task, task_id)


async def delete_task(task_id: int) -> bool:
    async with async_session() as session:
        task = await session.get(Task, task_id)
        if task is None:
            return False
        await session.delete(task)
        await session.commit()
        return True


async def is_task_completed(task_id: int, user_id: int) -> bool:
    async with async_session() as session:
        row = await session.execute(
            select(TaskCompletion.id).where(
                TaskCompletion.task_id == task_id,
                TaskCompletion.user_id == user_id,
            )
        )
        return row.first() is not None


async def complete_task(task_id: int, user_id: int) -> int | None:
    """Zadaniyani bajarilgan deb belgilaydi va so'm beradi (ATOMIK: UNIQUE
    constraint tufayli ikki marta berilmaydi). Berilgan so'mni qaytaradi,
    yoki allaqachon bajarilgan bo'lsa None."""
    async with async_session() as session:
        task = await session.get(Task, task_id)
        if task is None or not task.is_active:
            return None
        try:
            session.add(
                TaskCompletion(
                    task_id=task_id, user_id=user_id, reward=task.reward
                )
            )
            await session.flush()  # UNIQUE'ni shu yerda urib ko'ramiz
        except Exception:
            await session.rollback()
            return None

        user = await session.get(User, user_id)
        if user is not None:
            user.balance += task.reward
        await session.commit()
        return task.reward


# ================================================================== #
#  REQUIRED CHANNELS (majburiy obuna)
# ================================================================== #
async def add_required_channel(
    channel_id: str, title: str | None, url: str | None
) -> RequiredChannel:
    async with async_session() as session:
        ch = RequiredChannel(
            channel_id=channel_id, channel_title=title, channel_url=url
        )
        session.add(ch)
        await session.commit()
        await session.refresh(ch)
        return ch


async def get_required_channels() -> list[RequiredChannel]:
    async with async_session() as session:
        rows = await session.execute(
            select(RequiredChannel).where(
                RequiredChannel.is_active == True  # noqa: E712
            )
        )
        return list(rows.scalars().all())


async def delete_required_channel(ch_id: int) -> bool:
    async with async_session() as session:
        ch = await session.get(RequiredChannel, ch_id)
        if ch is None:
            return False
        await session.delete(ch)
        await session.commit()
        return True


# ================================================================== #
#  PROMOCODES
# ================================================================== #
async def create_promocode(code: str, reward: int, max_uses: int) -> Promocode | None:
    async with async_session() as session:
        exists = await session.execute(
            select(Promocode.id).where(Promocode.code == code)
        )
        if exists.first() is not None:
            return None
        promo = Promocode(code=code, reward=reward, max_uses=max_uses)
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
        return promo


async def get_all_promocodes() -> list[Promocode]:
    async with async_session() as session:
        rows = await session.execute(select(Promocode).order_by(Promocode.id.desc()))
        return list(rows.scalars().all())


async def redeem_promocode(code: str, user_id: int) -> tuple[str, int]:
    """Promokodni ishlatadi. Qaytaradi: (status, reward).
    status: 'ok' | 'not_found' | 'already' | 'limit' | 'inactive'
    """
    async with async_session() as session:
        promo = (
            await session.execute(
                select(Promocode).where(Promocode.code == code)
            )
        ).scalar_one_or_none()
        if promo is None:
            return ("not_found", 0)
        if not promo.is_active:
            return ("inactive", 0)
        if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
            return ("limit", 0)

        # Atomik: shu userning ishlatganini UNIQUE orqali ushlaymiz
        try:
            session.add(PromoUse(promo_id=promo.id, user_id=user_id))
            await session.flush()
        except Exception:
            await session.rollback()
            return ("already", 0)

        # Limitni qayta tekshirish (poyga holati)
        if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
            await session.rollback()
            return ("limit", 0)

        promo.used_count += 1
        user = await session.get(User, user_id)
        if user is not None:
            user.balance += promo.reward
        await session.commit()
        return ("ok", promo.reward)


# ================================================================== #
#  ORDERS & TRANSACTIONS (Payme)
# ================================================================== #
async def create_order(user_id: int, amount_som: int) -> Order:
    async with async_session() as session:
        order = Order(user_id=user_id, amount=amount_som, state="PENDING")
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order


async def get_order(order_id: int) -> Order | None:
    async with async_session() as session:
        return await session.get(Order, order_id)


async def mark_order_paid(order_id: int) -> Order | None:
    """Atomik: faqat PENDING → PAID o'tishida balansni to'ldiradi.
    Qaytaradi: yangilangan Order (balans qo'shilgan bo'lsa), aks holda None."""
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.state != "PENDING":
            return None
        order.state = "PAID"
        order.paid_at = datetime.utcnow()
        user = await session.get(User, order.user_id)
        if user is not None:
            user.balance += order.amount
        await session.commit()
        await session.refresh(order)
        return order


async def cancel_order(order_id: int) -> None:
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            return
        # To'langan bo'lsa — balansdan qaytarib olamiz (refund)
        if order.state == "PAID":
            user = await session.get(User, order.user_id)
            if user is not None:
                user.balance = max(0, user.balance - order.amount)
        order.state = "CANCELLED"
        await session.commit()


# ------- Transaction helpers (Payme JSON-RPC) ------- #
async def get_transaction_by_paycom_id(paycom_tx_id: str) -> Transaction | None:
    async with async_session() as session:
        row = await session.execute(
            select(Transaction).where(Transaction.paycom_tx_id == paycom_tx_id)
        )
        return row.scalar_one_or_none()


async def get_transactions_by_order(order_id: int) -> list[Transaction]:
    async with async_session() as session:
        rows = await session.execute(
            select(Transaction).where(Transaction.order_id == order_id)
        )
        return list(rows.scalars().all())


async def create_transaction(
    paycom_tx_id: str, order_id: int, amount_tiyin: int, paycom_time: int
) -> Transaction:
    async with async_session() as session:
        tx = Transaction(
            paycom_tx_id=paycom_tx_id,
            order_id=order_id,
            amount=amount_tiyin,
            state=1,
            paycom_time=paycom_time,
            create_time=int(time.time() * 1000),
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        return tx


async def perform_transaction(paycom_tx_id: str) -> Transaction | None:
    """Payme PerformTransaction: tranzaksiyani state=2 qiladi va buyurtmani
    to'langan deb belgilaydi (balans to'ldiriladi). Idempotent."""
    async with async_session() as session:
        tx = (
            await session.execute(
                select(Transaction).where(
                    Transaction.paycom_tx_id == paycom_tx_id
                )
            )
        ).scalar_one_or_none()
        if tx is None:
            return None
        if tx.state == 2:
            return tx  # allaqachon bajarilgan (idempotent)
        if tx.state != 1:
            return tx
        tx.state = 2
        tx.perform_time = int(time.time() * 1000)

        order = await session.get(Order, tx.order_id)
        if order is not None and order.state == "PENDING":
            order.state = "PAID"
            order.paid_at = datetime.utcnow()
            user = await session.get(User, order.user_id)
            if user is not None:
                user.balance += order.amount
        await session.commit()
        await session.refresh(tx)
        return tx


async def cancel_transaction(paycom_tx_id: str, reason: int) -> Transaction | None:
    """Payme CancelTransaction. state=1 → -1, state=2 → -2 (refund)."""
    async with async_session() as session:
        tx = (
            await session.execute(
                select(Transaction).where(
                    Transaction.paycom_tx_id == paycom_tx_id
                )
            )
        ).scalar_one_or_none()
        if tx is None:
            return None

        if tx.state in (-1, -2):
            # allaqachon bekor qilingan — reason'ni yangilaymiz, idempotent
            tx.reason = reason
            await session.commit()
            await session.refresh(tx)
            return tx

        order = await session.get(Order, tx.order_id)

        if tx.state == 2:
            # To'langan edi → refund
            new_state = -2
            if order is not None and order.state == "PAID":
                user = await session.get(User, order.user_id)
                if user is not None:
                    user.balance = max(0, user.balance - order.amount)
                order.state = "CANCELLED"
        else:
            new_state = -1
            if order is not None and order.state == "PENDING":
                order.state = "CANCELLED"

        tx.state = new_state
        tx.reason = reason
        tx.cancel_time = int(time.time() * 1000)
        await session.commit()
        await session.refresh(tx)
        return tx


# ================================================================== #
#  SETTINGS
# ================================================================== #
async def get_setting(key: str, default: str | None = None) -> str | None:
    async with async_session() as session:
        s = await session.get(Setting, key)
        return s.value if s and s.value is not None else default


async def set_setting(key: str, value: str | None) -> None:
    async with async_session() as session:
        s = await session.get(Setting, key)
        if s is None:
            session.add(Setting(key=key, value=value))
        else:
            s.value = value
        await session.commit()


# ================================================================== #
#  STATISTIKA
# ================================================================== #
async def get_stats() -> dict:
    async with async_session() as session:
        total_users = (
            await session.execute(select(func.count(User.id)))
        ).scalar_one()
        registered = (
            await session.execute(
                select(func.count(User.id)).where(
                    User.is_registered == True  # noqa: E712
                )
            )
        ).scalar_one()
        banned = (
            await session.execute(
                select(func.count(User.id)).where(
                    User.is_banned == True  # noqa: E712
                )
            )
        ).scalar_one()
        total_balance = (
            await session.execute(select(func.coalesce(func.sum(User.balance), 0)))
        ).scalar_one()
        paid_orders = (
            await session.execute(
                select(func.count(Order.id)).where(Order.state == "PAID")
            )
        ).scalar_one()
        total_paid = (
            await session.execute(
                select(func.coalesce(func.sum(Order.amount), 0)).where(
                    Order.state == "PAID"
                )
            )
        ).scalar_one()
        return {
            "total_users": total_users,
            "registered": registered,
            "banned": banned,
            "total_balance": total_balance,
            "paid_orders": paid_orders,
            "total_paid": total_paid,
        }
