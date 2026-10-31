"""SQLAlchemy modellar.

Barcha pul qiymatlari — SO'M (integer). Stars/bonus balans YO'Q.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------------ #
#  Foydalanuvchi
# ------------------------------------------------------------------ #
class User(Base):
    __tablename__ = "users"

    # Telegram user_id — asosiy kalit
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="uz")

    # Balans — faqat SO'M
    balance: Mapped[int] = mapped_column(Integer, default=0)

    # Ro'yxatdan o'tgan (til + telefon tasdiqlangan)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    # Referal
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # (eski maydon — endi ishlatilmaydi, moslik uchun qoldirilgan)
    ref_task_bonus_given: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    # Referal 3-kun oynasi uchun — ro'yxat (telefon tasdiqlangan) vaqti
    registered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ------------------------------------------------------------------ #
#  Zadaniya (reklama kanaliga obuna → so'm)
# ------------------------------------------------------------------ #
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Kanal: -100... chat_id yoki @username
    channel_id: Mapped[str] = mapped_column(String(64))
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Zadaniya bajarilganda beriladigan so'm (admin belgilaydi)
    reward: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # --- Bot orqali obunachi hisoblash + chegara ---
    # Bot avtomatik yaratgan invite link (bot admin bo'lganda)
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Bot linki orqali KIRGANLAR soni (chiqqanlar AYRILMAYDI — jami kirgan)
    joined_count: Mapped[int] = mapped_column(Integer, default=0)
    # Bot orqali kelib keyin CHIQIB ketganlar soni (faqat "faol" hisobi uchun)
    left_count: Mapped[int] = mapped_column(Integer, default=0)
    # Chegara (0 = cheksiz). joined_count shu songa yetganda adminга xabar
    sub_limit: Mapped[int] = mapped_column(Integer, default=0)
    # Chegara haqida admin'ga xabar berilganmi (bir marta)
    limit_notified: Mapped[bool] = mapped_column(Boolean, default=False)

    completions: Mapped[list["TaskCompletion"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class TaskCompletion(Base):
    __tablename__ = "task_completions"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    reward: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # --- Referal bonusi (3-kun oynasi) ---
    # Shu bajarish uchun EGAGA berilgan bonus (0 = egaga ketmagan)
    inviter_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    inviter_bonus: Mapped[int] = mapped_column(Integer, default=0)

    # --- Chiqib ketish nazorati (1 hafta) ---
    # Bonus hozir FAOL (berilgan va yechilmagan)mi?
    is_active_bonus: Mapped[bool] = mapped_column(Boolean, default=True)
    # Bonus chiqib ketganligi uchun yechib olinganmi?
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="completions")


# ------------------------------------------------------------------ #
#  Majburiy obuna kanallari
# ------------------------------------------------------------------ #
class RequiredChannel(Base):
    __tablename__ = "required_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64))
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # --- Bot orqali obunachi hisoblash + chegara (zadaniya kabi) ---
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_count: Mapped[int] = mapped_column(Integer, default=0)
    left_count: Mapped[int] = mapped_column(Integer, default=0)
    sub_limit: Mapped[int] = mapped_column(Integer, default=0)
    limit_notified: Mapped[bool] = mapped_column(Boolean, default=False)


# ------------------------------------------------------------------ #
#  Promokod (so'm beradi, har akkaunt 1 marta)
# ------------------------------------------------------------------ #
class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    reward: Mapped[int] = mapped_column(Integer, default=0)  # so'm
    # Necha marta ishlatish mumkin (0 = cheksiz)
    max_uses: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    uses: Mapped[list["PromoUse"]] = relationship(
        back_populates="promo", cascade="all, delete-orphan"
    )


class PromoUse(Base):
    __tablename__ = "promo_uses"
    __table_args__ = (
        UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promo_id: Mapped[int] = mapped_column(
        ForeignKey("promocodes.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    promo: Mapped["Promocode"] = relationship(back_populates="uses")


# ------------------------------------------------------------------ #
#  Balans to'ldirish (Payme)
# ------------------------------------------------------------------ #
#  order (topup) holatlari:
#    PENDING  — yaratildi, hali to'lanmagan
#    PAID     — to'landi (PerformTransaction)
#    CANCELLED— bekor qilindi
# ------------------------------------------------------------------ #
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    # So'mdagi summa (foydalanuvchi to'lovi)
    amount: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


# ------------------------------------------------------------------ #
#  Payme tranzaksiyasi (JSON-RPC)
# ------------------------------------------------------------------ #
#  Payme state kodlari:
#     1  — yaratildi (CreateTransaction)
#     2  — to'landi  (PerformTransaction)
#    -1  — yaratilgach bekor qilindi
#    -2  — to'langach bekor qilindi (refund)
# ------------------------------------------------------------------ #
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Payme tomonidan berilgan tranzaksiya ID
    paycom_tx_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE")
    )
    # Payme summasi — TIYIN (so'm * 100)
    amount: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Vaqtlar — Payme millisekundda kutadi
    paycom_time: Mapped[int] = mapped_column(BigInteger, default=0)
    create_time: Mapped[int] = mapped_column(BigInteger, default=0)
    perform_time: Mapped[int] = mapped_column(BigInteger, default=0)
    cancel_time: Mapped[int] = mapped_column(BigInteger, default=0)

    order: Mapped["Order"] = relationship(back_populates="transactions")


# ------------------------------------------------------------------ #
#  Sozlamalar (admin panel orqali o'zgartiriladigan kalit-qiymatlar)
# ------------------------------------------------------------------ #
class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(String(2048), nullable=True)
