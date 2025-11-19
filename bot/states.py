"""FSM States для бота"""
from aiogram.fsm.state import State, StatesGroup


class SendMessage(StatesGroup):
    """Состояния для отправки сообщения"""
    message_text = State()


class AddCourse(StatesGroup):
    """Состояния для добавления курса"""
    title = State()
    content = State()
    link = State()


class AddCompetition(StatesGroup):
    """Состояния для добавления конкурса"""
    title = State()
    content = State()
    deadline = State()
    link = State()


class CreateNews(StatesGroup):
    """Состояния для создания новости"""
    title = State()
    content = State()
    media = State()


class CreateContract(StatesGroup):
    """Состояния для создания договора"""
    select_partner = State()
    contract_type = State()
    contract_details = State()


class ResourceCenterQuestion(StatesGroup):
    """Состояния для вопроса в ресурсный центр"""
    question = State()
