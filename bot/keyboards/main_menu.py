from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура начального экрана"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Зарегистрироваться как организация", callback_data="register_org")
    builder.button(text="Зарегистрироваться как наставник", callback_data="register_mentor")
    builder.adjust(1)
    return builder.as_markup()


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="Найти партнёра")
    builder.button(text="Создать договор")
    builder.button(text="Новости")
    builder.button(text="Конкурсы")
    builder.button(text="Ресурсный центр")
    builder.button(text="Обучение")
    builder.button(text="Наставник")
    builder.button(text="Профиль")
    builder.button(text="Документы")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню администратора"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="Заявки на проверку")
    builder.button(text="Добавить курс")
    builder.button(text="Добавить конкурс")
    builder.button(text="Логи")
    builder.button(text="Статистика")
    builder.button(text="Главное меню")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="Отменить")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
