from aiogram.fsm.state import State, StatesGroup


class RegistrationOrg(StatesGroup):
    """Состояния регистрации организации"""
    name = State()
    legal_form = State()
    activity_field_or_okved = State()  # Зависит от legal_form
    inn = State()
    phone = State()
    email = State()
    telegram = State()
    description = State()
    turnover = State()
    can_give = State()
    can_give_other = State()
    need = State()
    need_other = State()
    interaction_format = State()
    city = State()
    partnership_type = State()
    gdpr_consent = State()


class RegistrationMentor(StatesGroup):
    """Состояния регистрации наставника"""
    name = State()
    expertise = State()
    experience = State()
    contact_info = State()
