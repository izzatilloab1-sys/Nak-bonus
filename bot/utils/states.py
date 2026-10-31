"""FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    language = State()
    phone = State()


class TopUp(StatesGroup):
    amount = State()


class PromoRedeem(StatesGroup):
    code = State()


class AdminAddTask(StatesGroup):
    channel = State()
    url = State()
    reward = State()
    limit = State()


class AdminAddChannel(StatesGroup):
    channel = State()
    url = State()
    limit = State()


class AdminCreatePromo(StatesGroup):
    code = State()
    reward = State()
    max_uses = State()


class AdminBroadcast(StatesGroup):
    message = State()


class AdminBalance(StatesGroup):
    user_id = State()
    amount = State()


class AdminBan(StatesGroup):
    user_id = State()


class AdminRefLookup(StatesGroup):
    user_id = State()


class AdminBackupChannel(StatesGroup):
    channel = State()


class AdminPayment(StatesGroup):
    # Umumiy qiymat kiritish (qaysi kalit — FSM data'da saqlanadi)
    value = State()
