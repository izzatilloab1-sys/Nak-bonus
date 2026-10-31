"""Ikki tilli matnlar (uz / ru) — oddiy i18n."""
from __future__ import annotations

TEXTS: dict[str, dict[str, str]] = {
    # ---------------- Registratsiya ---------------- #
    "choose_language": {
        "uz": "🌐 Tilni tanlang:",
        "ru": "🌐 Выберите язык:",
    },
    "language_set": {
        "uz": "✅ Til tanlandi: O'zbek tili",
        "ru": "✅ Язык выбран: Русский",
    },
    "ask_phone": {
        "uz": (
            "📱 Ro'yxatdan o'tish uchun telefon raqamingizni yuboring.\n\n"
            "Pastdagi <b>«📱 Telefon raqamni yuborish»</b> tugmasini bosing.\n"
            "⚠️ Raqamni qo'lda yozib bo'lmaydi — faqat tugma orqali yuboring."
        ),
        "ru": (
            "📱 Для регистрации отправьте свой номер телефона.\n\n"
            "Нажмите кнопку <b>«📱 Отправить номер телефона»</b> снизу.\n"
            "⚠️ Ввести номер вручную нельзя — только через кнопку."
        ),
    },
    "phone_button": {
        "uz": "📱 Telefon raqamni yuborish",
        "ru": "📱 Отправить номер телефона",
    },
    "phone_manual_rejected": {
        "uz": (
            "❌ Raqamni qo'lda yozish mumkin emas.\n"
            "Iltimos, pastdagi <b>«📱 Telefon raqamni yuborish»</b> "
            "tugmasidan foydalaning."
        ),
        "ru": (
            "❌ Нельзя вводить номер вручную.\n"
            "Пожалуйста, используйте кнопку "
            "<b>«📱 Отправить номер телефона»</b> снизу."
        ),
    },
    "phone_not_own": {
        "uz": "❌ Faqat <b>o'zingizning</b> raqamingizni yuboring.",
        "ru": "❌ Отправьте только <b>свой</b> номер телефона.",
    },
    "registration_done": {
        "uz": "✅ Ro'yxatdan o'tish yakunlandi! Xush kelibsiz 🎉",
        "ru": "✅ Регистрация завершена! Добро пожаловать 🎉",
    },

    # ---------------- Majburiy obuna ---------------- #
    "must_subscribe": {
        "uz": (
            "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, "
            "so'ng <b>«✅ Tekshirish»</b> tugmasini bosing:"
        ),
        "ru": (
            "📢 Чтобы пользоваться ботом, подпишитесь на каналы ниже, "
            "затем нажмите <b>«✅ Проверить»</b>:"
        ),
    },
    "check_subscription": {
        "uz": "✅ Tekshirish",
        "ru": "✅ Проверить",
    },
    "not_subscribed": {
        "uz": "❌ Siz hali barcha kanallarga obuna bo'lmadingiz.",
        "ru": "❌ Вы ещё не подписались на все каналы.",
    },
    "subscribed_ok": {
        "uz": "✅ Rahmat! Obuna tasdiqlandi.",
        "ru": "✅ Спасибо! Подписка подтверждена.",
    },

    # ---------------- Asosiy menyu ---------------- #
    "main_menu": {
        "uz": "🏠 Asosiy menyu. Kerakli bo'limni tanlang:",
        "ru": "🏠 Главное меню. Выберите раздел:",
    },
    "btn_balance": {"uz": "💰 Balans", "ru": "💰 Баланс"},
    "btn_tasks": {"uz": "🎯 Vazifalar", "ru": "🎯 Задания"},
    "btn_referral": {"uz": "👥 Referal", "ru": "👥 Реферал"},
    "btn_promo": {"uz": "🎁 Promokod", "ru": "🎁 Промокод"},
    "btn_topup": {"uz": "💳 Balansni to'ldirish", "ru": "💳 Пополнить баланс"},
    "btn_language": {"uz": "🌐 Til", "ru": "🌐 Язык"},
    "btn_admin": {"uz": "🛠 Admin panel", "ru": "🛠 Админ панель"},
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена"},
    "cancelled": {"uz": "❌ Bekor qilindi.", "ru": "❌ Отменено."},

    # ---------------- Balans ---------------- #
    "balance_info": {
        "uz": "💰 Sizning balansingiz: <b>{balance:,} so'm</b>",
        "ru": "💰 Ваш баланс: <b>{balance:,} сум</b>",
    },

    # ---------------- Vazifalar ---------------- #
    "tasks_title": {
        "uz": "🎯 Mavjud vazifalar. Kanalga obuna bo'lib, tekshiring:",
        "ru": "🎯 Доступные задания. Подпишитесь на канал и проверьте:",
    },
    "no_tasks": {
        "uz": "😔 Hozircha vazifalar yo'q.",
        "ru": "😔 Пока нет заданий.",
    },
    "task_item": {
        "uz": "📢 {title}\n💵 Mukofot: <b>{reward:,} so'm</b>",
        "ru": "📢 {title}\n💵 Награда: <b>{reward:,} сум</b>",
    },
    "task_not_subscribed": {
        "uz": "❌ Siz bu kanalga obuna bo'lmadingiz. Obuna bo'ling va qayta tekshiring.",
        "ru": "❌ Вы не подписаны на этот канал. Подпишитесь и проверьте снова.",
    },
    "task_already_done": {
        "uz": "ℹ️ Bu vazifa allaqachon bajarilgan.",
        "ru": "ℹ️ Это задание уже выполнено.",
    },
    "task_reward_given": {
        "uz": "✅ Vazifa bajarildi! <b>+{reward:,} so'm</b> qo'shildi.",
        "ru": "✅ Задание выполнено! <b>+{reward:,} сум</b> начислено.",
    },
    "btn_task_check": {"uz": "✅ Tekshirish", "ru": "✅ Проверить"},
    "btn_task_open": {"uz": "➡️ Kanalga o'tish", "ru": "➡️ Перейти в канал"},

    # ---------------- Referal ---------------- #
    "referral_info": {
        "uz": (
            "👥 <b>Referal dastur</b>\n\n"
            "Do'stlaringizni taklif qiling va so'm ishlang!\n\n"
            "• Har bir yangi do'st ro'yxatdan o'tganda: "
            "<b>+{join:,} so'm</b>\n"
            "• U vazifa bajarganda qo'shimcha: <b>+{task:,} so'm</b>\n\n"
            "👤 Taklif qilganlaringiz: <b>{count}</b> ta\n\n"
            "🔗 Sizning havolangiz:\n{link}"
        ),
        "ru": (
            "👥 <b>Реферальная программа</b>\n\n"
            "Приглашайте друзей и зарабатывайте сум!\n\n"
            "• За каждого нового друга при регистрации: "
            "<b>+{join:,} сум</b>\n"
            "• Когда он выполнит задание, дополнительно: <b>+{task:,} сум</b>\n\n"
            "👤 Вы пригласили: <b>{count}</b> чел.\n\n"
            "🔗 Ваша ссылка:\n{link}"
        ),
    },
    "referral_join_notify": {
        "uz": "🎉 Yangi referal! Sizga <b>+{amount:,} so'm</b> qo'shildi.",
        "ru": "🎉 Новый реферал! Вам начислено <b>+{amount:,} сум</b>.",
    },
    "referral_task_notify": {
        "uz": (
            "🎉 Sizning referalingiz vazifa bajardi! "
            "Sizga <b>+{amount:,} so'm</b> qo'shildi."
        ),
        "ru": (
            "🎉 Ваш реферал выполнил задание! "
            "Вам начислено <b>+{amount:,} сум</b>."
        ),
    },

    # ---------------- Promokod ---------------- #
    "promo_ask": {
        "uz": "🎁 Promokodni kiriting:",
        "ru": "🎁 Введите промокод:",
    },
    "promo_ok": {
        "uz": "✅ Promokod qabul qilindi! <b>+{reward:,} so'm</b> qo'shildi.",
        "ru": "✅ Промокод принят! <b>+{reward:,} сум</b> начислено.",
    },
    "promo_not_found": {
        "uz": "❌ Bunday promokod topilmadi.",
        "ru": "❌ Такой промокод не найден.",
    },
    "promo_already": {
        "uz": "ℹ️ Siz bu promokodni allaqachon ishlatgansiz.",
        "ru": "ℹ️ Вы уже использовали этот промокод.",
    },
    "promo_limit": {
        "uz": "❌ Bu promokod limiti tugagan.",
        "ru": "❌ Лимит этого промокода исчерпан.",
    },
    "promo_inactive": {
        "uz": "❌ Bu promokod faol emas.",
        "ru": "❌ Этот промокод неактивен.",
    },

    # ---------------- Balans to'ldirish (Payme) ---------------- #
    "topup_choose": {
        "uz": (
            "💳 Balansni to'ldirish summasini tanlang yoki "
            "<b>«✏️ Boshqa summa»</b> orqali o'zingiz kiriting.\n\n"
            "Minimal summa: <b>{min:,} so'm</b>"
        ),
        "ru": (
            "💳 Выберите сумму пополнения или введите свою через "
            "<b>«✏️ Другая сумма»</b>.\n\n"
            "Минимальная сумма: <b>{min:,} сум</b>"
        ),
    },
    "topup_custom": {"uz": "✏️ Boshqa summa", "ru": "✏️ Другая сумма"},
    "topup_ask_custom": {
        "uz": "✏️ To'ldirmoqchi bo'lgan summangizni so'mda yozing (masalan 15000):",
        "ru": "✏️ Напишите сумму пополнения в сумах (например 15000):",
    },
    "topup_too_small": {
        "uz": "❌ Minimal summa <b>{min:,} so'm</b>. Qaytadan kiriting.",
        "ru": "❌ Минимальная сумма <b>{min:,} сум</b>. Введите ещё раз.",
    },
    "topup_invalid": {
        "uz": "❌ Noto'g'ri summa. Faqat raqam kiriting (masalan 15000).",
        "ru": "❌ Неверная сумма. Введите только число (например 15000).",
    },
    "topup_link": {
        "uz": (
            "💳 <b>{amount:,} so'm</b> to'lash uchun quyidagi tugmani bosing.\n\n"
            "To'lov muvaffaqiyatli bo'lgach, balansingiz avtomatik to'ldiriladi."
        ),
        "ru": (
            "💳 Нажмите кнопку ниже, чтобы оплатить <b>{amount:,} сум</b>.\n\n"
            "После успешной оплаты баланс пополнится автоматически."
        ),
    },
    "topup_pay_button": {"uz": "💳 Payme orqali to'lash", "ru": "💳 Оплатить через Payme"},
    "topup_success_notify": {
        "uz": "✅ To'lov qabul qilindi! Balansingizga <b>+{amount:,} so'm</b> qo'shildi.",
        "ru": "✅ Оплата принята! На баланс начислено <b>+{amount:,} сум</b>.",
    },

    # ---------------- Umumiy ---------------- #
    "banned": {
        "uz": "🚫 Siz botdan foydalanish huquqidan mahrum qilingansiz.",
        "ru": "🚫 Вы заблокированы и не можете пользоваться ботом.",
    },
    "not_registered": {
        "uz": "ℹ️ Avval ro'yxatdan o'ting. /start bosing.",
        "ru": "ℹ️ Сначала зарегистрируйтесь. Нажмите /start.",
    },
}


def t(key: str, lang: str = "uz", **kwargs) -> str:
    """Matnni tanlangan tilda qaytaradi (uz — default)."""
    entry = TEXTS.get(key, {})
    text = entry.get(lang) or entry.get("uz") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text
