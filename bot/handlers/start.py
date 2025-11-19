from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from database import crud
from bot.keyboards.main_menu import get_start_keyboard, get_main_menu_keyboard, get_admin_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if user:
        # Пользователь уже зарегистрирован
        if user['role'] in ['admin', 'owner']:
            await message.answer(
                f"Добро пожаловать, {user['full_name'] or 'Администратор'}!",
                reply_markup=get_admin_menu_keyboard()
            )
        else:
            await message.answer(
                f"С возвращением, {user['full_name'] or message.from_user.full_name}!",
                reply_markup=get_main_menu_keyboard()
            )
    else:
        # Новый пользователь - предлагаем регистрацию
        await message.answer(
            "<b>Добро пожаловать в Партнёрский Центр Организаций!</b>\n\n"
            "Этот бот поможет вам:\n"
            "✅ Найти партнёров для вашего бизнеса\n"
            "✅ Создавать договоры\n"
            "✅ Получать информацию о конкурсах и финансировании\n"
            "✅ Найти наставника\n\n"
            "Для начала работы выберите тип регистрации:",
            reply_markup=get_start_keyboard()
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Обработчик команды /menu - возврат к главному меню"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if user:
        if user['role'] in ["admin", "owner"]:
            await message.answer(
                "Админ-панель:",
                reply_markup=get_admin_menu_keyboard()
            )
        else:
            await message.answer(
                "Главное меню:",
                reply_markup=get_main_menu_keyboard()
            )
    else:
        await message.answer(
            "Вы не зарегистрированы. Используйте /start для регистрации."
        )
