from aiogram.fsm.state import State, StatesGroup


class SendMessage(StatesGroup):
    """Состояния для отправки сообщения от имени сервиса"""
    message_text = State()
    verification_id = State()
    action = State()  # approve или reject
