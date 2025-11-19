from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config.config import settings


def get_legal_form_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора юридической формы"""
    builder = InlineKeyboardBuilder()
    for form in settings.LEGAL_FORMS:
        builder.button(text=form, callback_data=f"legal_form:{form}")
    builder.adjust(2)
    return builder.as_markup()


def get_turnover_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора оборотов"""
    builder = InlineKeyboardBuilder()
    for turnover in settings.TURNOVER_RANGES:
        builder.button(text=turnover, callback_data=f"turnover:{turnover}")
    builder.adjust(2)
    return builder.as_markup()


def get_partnership_options_keyboard(option_type: str, selected: list = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора опций партнерства (что может дать/что нужно)"""
    builder = InlineKeyboardBuilder()
    options = settings.CAN_GIVE_OPTIONS if option_type == "can_give" else settings.NEED_OPTIONS
    selected = selected or []

    for option in options:
        # Добавляем галочку если опция выбрана
        text = f"✅ {option}" if option in selected else option
        builder.button(text=text, callback_data=f"{option_type}:{option}")

    builder.button(text="Иное (ручной ввод)", callback_data=f"{option_type}:other")
    builder.button(text="✔️ Готово", callback_data=f"{option_type}:done")
    builder.adjust(2)
    return builder.as_markup()


def get_interaction_format_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора формата взаимодействия"""
    builder = InlineKeyboardBuilder()
    for format_type in settings.INTERACTION_FORMATS:
        builder.button(text=format_type, callback_data=f"interaction:{format_type}")
    builder.adjust(2)
    return builder.as_markup()


def get_partnership_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа партнерства"""
    builder = InlineKeyboardBuilder()
    for p_type in settings.PARTNERSHIP_TYPES:
        builder.button(text=p_type, callback_data=f"partnership_type:{p_type}")
    builder.adjust(2)
    return builder.as_markup()


def get_gdpr_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура согласия на обработку персональных данных"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Согласен", callback_data="gdpr:accept")
    builder.button(text="Не согласен", callback_data="gdpr:decline")
    builder.adjust(1)
    return builder.as_markup()


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура Да/Нет"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="yes")
    builder.button(text="Нет", callback_data="no")
    builder.adjust(2)
    return builder.as_markup()
