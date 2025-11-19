"""Хендлеры для владельца (owner) - управление админами и операторами"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import crud
from config.config import settings

router = Router()


class AddAdmin(StatesGroup):
    """Состояния для добавления администратора"""
    telegram_id = State()


def is_owner(telegram_id: int) -> bool:
    """Проверка прав владельца по telegram_id из конфига"""
    return telegram_id == settings.OWNER_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin - управление операторами"""
    if not is_owner(message.from_user.id):
        await message.answer("❌ Эта команда доступна только владельцу!")
        return

    # Получаем список всех админов
    admins = await crud.get_admins()
    admin_list = []
    for admin in admins:
        if admin['role'] == 'owner':
            admin_list.append(f"👑 {admin['full_name']} (@{admin['username'] or 'нет'}) - OWNER")
        else:
            admin_list.append(f"👨‍💼 {admin['full_name']} (@{admin['username'] or 'нет'}) - Админ")

    admin_text = "\n".join(admin_list) if admin_list else "Нет администраторов"

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить оператора", callback_data="admin:add")
    builder.button(text="➖ Удалить оператора", callback_data="admin:remove")
    builder.button(text="📋 Список всех админов", callback_data="admin:list")
    builder.adjust(1)

    await message.answer(
        f"<b>🔧 Панель управления операторами</b>\n\n"
        f"<b>Текущие операторы:</b>\n{admin_text}",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin:add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления администратора"""
    if not is_owner(callback.from_user.id):
        await callback.answer("Недостаточно прав!", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>➕ Добавление оператора</b>\n\n"
        "Введите Telegram ID пользователя, которого хотите сделать оператором.\n\n"
        "Пользователь может узнать свой ID у бота @userinfobot"
    )
    await state.set_state(AddAdmin.telegram_id)
    await callback.answer()


@router.message(AddAdmin.telegram_id)
async def admin_add_process(message: Message, state: FSMContext):
    """Обработка добавления администратора"""
    try:
        telegram_id = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат! Введите числовой Telegram ID.")
        return

    # Проверяем существует ли пользователь
    target_user = await crud.get_user_by_telegram_id(telegram_id)

    if not target_user:
        await message.answer(
            "❌ Пользователь с таким ID не найден в системе.\n"
            "Пользователь должен сначала начать работу с ботом (/start)."
        )
        await state.clear()
        return

    # Проверяем не является ли уже админом
    if target_user['role'] in ['admin', 'owner']:
        await message.answer(
            f"ℹ️ Этот пользователь уже является {target_user['role']}!"
        )
        await state.clear()
        return

    # Обновляем роль на admin
    await crud.update_user_role(telegram_id, 'admin')

    # Уведомляем нового админа
    from aiogram import Bot
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        await bot.send_message(
            telegram_id,
            "🎉 <b>Поздравляем!</b>\n\n"
            "Вам назначена роль <b>Администратора</b> платформы!\n\n"
            "Теперь вы можете:\n"
            "• Проверять заявки организаций\n"
            "• Одобрять/отклонять регистрации\n"
            "• Добавлять курсы и конкурсы\n"
            "• Просматривать статистику\n\n"
            "Используйте кнопку <b>«Заявки на проверку»</b> в главном меню.",
            parse_mode='HTML'
        )
    except:
        pass
    await bot.session.close()

    await message.answer(
        f"✅ Пользователь {target_user['full_name']} успешно назначен администратором!"
    )
    await state.clear()


@router.callback_query(F.data == "admin:remove")
async def admin_remove(callback: CallbackQuery):
    """Удаление администратора"""
    if not is_owner(callback.from_user.id):
        await callback.answer("Недостаточно прав!", show_alert=True)
        return

    # Получаем всех админов (кроме owner)
    admins = await crud.get_admins()
    non_owner_admins = [a for a in admins if a['role'] == 'admin']

    if not non_owner_admins:
        await callback.answer("Нет администраторов для удаления", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for admin in non_owner_admins:
        builder.button(
            text=f"❌ {admin['full_name']} (@{admin['username'] or 'нет'})",
            callback_data=f"remove_admin:{admin['telegram_id']}"
        )
    builder.button(text="« Назад", callback_data="admin:back")
    builder.adjust(1)

    await callback.message.edit_text(
        "<b>Выберите администратора для удаления:</b>",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_admin:"))
async def admin_remove_confirm(callback: CallbackQuery):
    """Подтверждение удаления администратора"""
    telegram_id = int(callback.data.split(":")[1])

    if not is_owner(callback.from_user.id):
        await callback.answer("Недостаточно прав!", show_alert=True)
        return

    target_user = await crud.get_user_by_telegram_id(telegram_id)

    # Обновляем роль обратно на organization
    await crud.update_user_role(telegram_id, 'organization')

    # Уведомляем бывшего админа
    from aiogram import Bot
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        await bot.send_message(
            telegram_id,
            "ℹ️ Вы больше не являетесь администратором платформы."
        )
    except:
        pass
    await bot.session.close()

    await callback.message.edit_text(
        f"✅ Пользователь {target_user['full_name']} удален из администраторов."
    )
    await callback.answer()


@router.callback_query(F.data == "admin:list")
async def admin_list(callback: CallbackQuery):
    """Список всех администраторов"""
    if not is_owner(callback.from_user.id):
        await callback.answer("Недостаточно прав!", show_alert=True)
        return

    admins = await crud.get_admins()
    admin_text = []

    for admin in admins:
        role_emoji = "👑" if admin['role'] == 'owner' else "👨‍💼"
        role_text = "OWNER" if admin['role'] == 'owner' else "Админ"
        admin_text.append(
            f"{role_emoji} <b>{admin['full_name']}</b>\n"
            f"   @{admin['username'] or 'нет'} | ID: {admin['telegram_id']}\n"
            f"   Роль: {role_text}"
        )

    text = "\n\n".join(admin_text) if admin_text else "Нет администраторов"

    builder = InlineKeyboardBuilder()
    builder.button(text="« Назад", callback_data="admin:back")
    builder.adjust(1)

    await callback.message.edit_text(
        f"<b>📋 Список всех операторов:</b>\n\n{text}",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery):
    """Возврат к панели управления"""
    if not is_owner(callback.from_user.id):
        await callback.answer("Недостаточно прав!", show_alert=True)
        return

    # Получаем список всех админов
    admins = await crud.get_admins()
    admin_list = []
    for admin in admins:
        if admin['role'] == 'owner':
            admin_list.append(f"👑 {admin['full_name']} (@{admin['username'] or 'нет'}) - OWNER")
        else:
            admin_list.append(f"👨‍💼 {admin['full_name']} (@{admin['username'] or 'нет'}) - Админ")

    admin_text = "\n".join(admin_list) if admin_list else "Нет администраторов"

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить оператора", callback_data="admin:add")
    builder.button(text="➖ Удалить оператора", callback_data="admin:remove")
    builder.button(text="📋 Список всех админов", callback_data="admin:list")
    builder.adjust(1)

    await callback.message.edit_text(
        f"<b>🔧 Панель управления операторами</b>\n\n"
        f"<b>Текущие операторы:</b>\n{admin_text}",
        reply_markup=builder.as_markup()
    )
    await callback.answer()
