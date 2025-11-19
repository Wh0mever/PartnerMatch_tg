from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

from database import crud
from config.config import settings
from bot.states import SendMessage, AddCourse, AddCompetition

router = Router()


def is_admin(user_role: str) -> bool:
    """Проверка прав администратора"""
    return user_role in ["admin", "owner"]


@router.message(F.text == "Заявки на проверку")
async def view_pending_verifications(message: Message):
    """Просмотр заявок на проверку"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user or not is_admin(user['role']):
        await message.answer("У вас нет прав администратора!")
        return

    # Получаем все заявки на проверку
    verifications = await crud.get_pending_verifications()

    if not verifications:
        await message.answer("Нет заявок на проверку.")
        return

    # Группируем данные (в SQLite JOIN возвращает все колонки)
    seen_ids = set()
    for row in verifications:
        verification_id = row['id']
        if verification_id in seen_ids:
            continue
        seen_ids.add(verification_id)

        # Получаем организацию
        org = await crud.get_organization_by_id(row['organization_id'])

        card = f"<b>Заявка #{verification_id}</b>\n\n"
        card += f"Организация: <b>{org['name']}</b>\n"
        card += f"ИНН: {org['inn']}\n"
        card += f"Юр. форма: {org['legal_form']}\n"
        card += f"Телефон: {org['phone']}\n"
        card += f"Email: {org['email']}\n"
        card += f"Telegram: {org['telegram']}\n\n"
        card += f"Оборот: {org['turnover']}\n"
        card += f"Формат: {org['interaction_format']}\n"
        if org.get('city'):
            card += f"Город: {org['city']}\n"
        card += f"\nОписание: {org['description']}"

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Одобрить", callback_data=f"verify:approve:{verification_id}")
        builder.button(text="✅ Одобрить + Сообщение", callback_data=f"verify:approve_msg:{verification_id}")
        builder.button(text="❌ Отклонить", callback_data=f"verify:reject:{verification_id}")
        builder.button(text="❌ Отклонить + Сообщение", callback_data=f"verify:reject_msg:{verification_id}")
        builder.adjust(2)

        await message.answer(card, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("verify:approve:"))
async def approve_verification(callback: CallbackQuery):
    """Одобрение заявки"""
    verification_id = int(callback.data.split(":")[2])

    user = await crud.get_user_by_telegram_id(callback.from_user.id)

    if not user or not is_admin(user['role']):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    # Обновляем верификацию
    verification = await crud.get_verification_by_id(verification_id)
    await crud.update_verification(verification_id, user['id'], 'approved', None)

    # Обновляем статус организации
    await crud.update_organization_status(verification['organization_id'], 'verified')

    # Логируем
    await crud.create_log(user['id'], "verification_approve", {"organization_id": verification['organization_id']})

    # Уведомляем пользователя
    org = await crud.get_organization_by_id(verification['organization_id'])
    org_user = await crud.get_user_by_id(org['user_id'])

    from aiogram import Bot
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        await bot.send_message(
            org_user['telegram_id'],
            "✅ <b>Поздравляем!</b>\n\n"
            "Ваша организация успешно верифицирована!\n"
            "Теперь вы можете искать партнеров и пользоваться всеми функциями платформы."
        )
    except:
        pass
    await bot.session.close()

    await callback.message.edit_text(
        f"✅ Заявка #{verification_id} одобрена!"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("verify:reject:"))
async def reject_verification(callback: CallbackQuery):
    """Отклонение заявки"""
    verification_id = int(callback.data.split(":")[2])

    user = await crud.get_user_by_telegram_id(callback.from_user.id)

    if not user or not is_admin(user['role']):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    # Обновляем верификацию
    verification = await crud.get_verification_by_id(verification_id)
    await crud.update_verification(verification_id, user['id'], 'rejected', "Не прошла проверку администратора")

    # Обновляем статус организации
    await crud.update_organization_status(verification['organization_id'], 'rejected')

    # Логируем
    await crud.create_log(user['id'], "verification_reject", {"organization_id": verification['organization_id']})

    # Уведомляем пользователя
    org = await crud.get_organization_by_id(verification['organization_id'])
    org_user = await crud.get_user_by_id(org['user_id'])

    from aiogram import Bot
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        await bot.send_message(
            org_user['telegram_id'],
            "❌ К сожалению, ваша заявка отклонена.\n\n"
            "Причина: Не прошла проверку администратора\n\n"
            "Для получения дополнительной информации обратитесь к администратору."
        )
    except:
        pass
    await bot.session.close()

    await callback.message.edit_text(
        f"❌ Заявка #{verification_id} отклонена!"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("verify:approve_msg:"))
async def approve_with_message_start(callback: CallbackQuery, state: FSMContext):
    """Начало одобрения с сообщением"""
    verification_id = int(callback.data.split(":")[2])

    user = await crud.get_user_by_telegram_id(callback.from_user.id)
    if not user or not is_admin(user['role']):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    await state.update_data(verification_id=verification_id, action="approve")
    await callback.message.edit_text(
        "✍️ <b>Одобрение с сообщением</b>\n\n"
        "Напишите персональное сообщение, которое будет отправлено организации от имени сервиса.\n\n"
        "Это сообщение будет добавлено к стандартному уведомлению об одобрении."
    )
    await state.set_state(SendMessage.message_text)
    await callback.answer()


@router.callback_query(F.data.startswith("verify:reject_msg:"))
async def reject_with_message_start(callback: CallbackQuery, state: FSMContext):
    """Начало отклонения с сообщением"""
    verification_id = int(callback.data.split(":")[2])

    user = await crud.get_user_by_telegram_id(callback.from_user.id)
    if not user or not is_admin(user['role']):
        await callback.answer("У вас нет прав!", show_alert=True)
        return

    await state.update_data(verification_id=verification_id, action="reject")
    await callback.message.edit_text(
        "✍️ <b>Отклонение с сообщением</b>\n\n"
        "Напишите причину отклонения и дополнительную информацию для организации.\n\n"
        "Это сообщение будет отправлено пользователю от имени сервиса."
    )
    await state.set_state(SendMessage.message_text)
    await callback.answer()


@router.message(SendMessage.message_text)
async def process_custom_message(message: Message, state: FSMContext):
    """Обработка пользовательского сообщения"""
    data = await state.get_data()
    verification_id = data['verification_id']
    action = data['action']
    custom_message = message.text

    user = await crud.get_user_by_telegram_id(message.from_user.id)

    # Обновляем верификацию
    verification = await crud.get_verification_by_id(verification_id)

    if action == "approve":
        await crud.update_verification(verification_id, user['id'], 'approved', None)
        await crud.update_organization_status(verification['organization_id'], 'verified')
        await crud.create_log(user['id'], "verification_approve", {"organization_id": verification['organization_id']})

        org = await crud.get_organization_by_id(verification['organization_id'])
        org_user = await crud.get_user_by_id(org['user_id'])

        from aiogram import Bot
        bot = Bot(token=settings.BOT_TOKEN)
        try:
            await bot.send_message(
                org_user['telegram_id'],
                f"✅ <b>Поздравляем!</b>\n\n"
                f"Ваша организация успешно верифицирована!\n\n"
                f"📩 <b>Сообщение от администратора:</b>\n{custom_message}\n\n"
                f"Теперь вы можете искать партнеров и пользоваться всеми функциями платформы."
            )
        except:
            pass
        await bot.session.close()

        await message.answer(
            f"✅ Заявка #{verification_id} одобрена!\n"
            f"Персональное сообщение отправлено организации."
        )

    else:  # reject
        await crud.update_verification(verification_id, user['id'], 'rejected', custom_message)
        await crud.update_organization_status(verification['organization_id'], 'rejected')
        await crud.create_log(user['id'], "verification_reject", {"organization_id": verification['organization_id']})

        org = await crud.get_organization_by_id(verification['organization_id'])
        org_user = await crud.get_user_by_id(org['user_id'])

        from aiogram import Bot
        bot = Bot(token=settings.BOT_TOKEN)
        try:
            await bot.send_message(
                org_user['telegram_id'],
                f"❌ К сожалению, ваша заявка отклонена.\n\n"
                f"📩 <b>Сообщение от администратора:</b>\n{custom_message}\n\n"
                f"Для получения дополнительной информации обратитесь к администратору."
            )
        except:
            pass
        await bot.session.close()

        await message.answer(
            f"❌ Заявка #{verification_id} отклонена.\n"
            f"Сообщение с причиной отправлено организации."
        )

    await state.clear()


@router.message(F.text == "Статистика")
async def show_statistics(message: Message):
    """Показать статистику платформы"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user or not is_admin(user['role']):
        await message.answer("У вас нет прав администратора!")
        return

    stats_data = await crud.get_statistics()

    stats = f"<b>📊 Статистика платформы</b>\n\n"
    stats += f"👥 Всего пользователей: {stats_data['total_users']}\n"
    stats += f"🏢 Всего организаций: {stats_data['total_orgs']}\n"
    stats += f"✅ Верифицированных: {stats_data['verified_orgs']}\n"
    stats += f"⏳ На проверке: {stats_data['pending_orgs']}\n"
    stats += f"🤝 Всего матчей: {stats_data['total_matches']}"

    await message.answer(stats)


# ============= ОБРАБОТЧИКИ КНОПОК МОДЕРАЦИИ =============

@router.callback_query(F.data.startswith("verify_approve:"))
async def verify_approve(callback: CallbackQuery):
    """Одобрение заявки"""
    org_id = int(callback.data.split(":")[1])

    user = await crud.get_user_by_telegram_id(callback.from_user.id)
    if not user or not is_admin(user['role']):
        await callback.answer("Недостаточно прав!", show_alert=True)
        return

    # Одобряем заявку
    await crud.approve_verification(org_id, user['id'])

    # Получаем информацию об организации
    org = await crud.get_organization_by_id(org_id)
    org_user = await crud.get_user_by_id(org['user_id'])

    # Уведомляем организацию
    from aiogram import Bot
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        await bot.send_message(
            org_user['telegram_id'],
            "🎉 <b>Поздравляем!</b>\n\n"
            "Ваша заявка на регистрацию <b>одобрена</b>!\n\n"
            "Теперь вы можете:\n"
            "• Искать партнёров\n"
            "• Создавать договоры\n"
            "• Публиковать новости\n"
            "• Общаться с другими организациями\n\n"
            "Используйте главное меню для доступа ко всем функциям.",
            parse_mode='HTML'
        )
    except:
        pass
    await bot.session.close()

    # Обновляем сообщение
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"✅ <b>Заявка одобрена</b> администратором {user['full_name']}",
        parse_mode='HTML'
    )
    await callback.answer("✅ Заявка одобрена!")


@router.callback_query(F.data.startswith("verify_reject:"))
async def verify_reject(callback: CallbackQuery):
    """Отклонение заявки"""
    org_id = int(callback.data.split(":")[1])

    user = await crud.get_user_by_telegram_id(callback.from_user.id)
    if not user or not is_admin(user['role']):
        await callback.answer("Недостаточно прав!", show_alert=True)
        return

    # Отклоняем заявку
    await crud.reject_verification(org_id, user['id'], "Отклонено администратором")

    # Получаем информацию об организации
    org = await crud.get_organization_by_id(org_id)
    org_user = await crud.get_user_by_id(org['user_id'])

    # Уведомляем организацию
    from aiogram import Bot
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        await bot.send_message(
            org_user['telegram_id'],
            "❌ <b>Заявка отклонена</b>\n\n"
            "К сожалению, ваша заявка на регистрацию была отклонена администратором.\n\n"
            "Причина: Отклонено администратором\n\n"
            "Вы можете связаться с поддержкой для уточнения деталей.",
            parse_mode='HTML'
        )
    except:
        pass
    await bot.session.close()

    # Обновляем сообщение
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"❌ <b>Заявка отклонена</b> администратором {user['full_name']}",
        parse_mode='HTML'
    )
    await callback.answer("❌ Заявка отклонена!")


# ========== ДОБАВЛЕНИЕ КУРСОВ ==========

@router.message(F.text == "Добавить курс")
async def add_course_start(message: Message, state: FSMContext):
    """Начало добавления курса"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user or not is_admin(user['role']):
        await message.answer("У вас нет прав администратора!")
        return

    await message.answer(
        "Введите название курса:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AddCourse.title)


@router.message(AddCourse.title)
async def add_course_title(message: Message, state: FSMContext):
    """Получение названия курса"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Добавление курса отменено")
        return

    await state.update_data(title=message.text)
    await message.answer("Введите описание курса:")
    await state.set_state(AddCourse.content)


@router.message(AddCourse.content)
async def add_course_content(message: Message, state: FSMContext):
    """Получение описания курса"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Добавление курса отменено")
        return

    await state.update_data(content=message.text)
    await message.answer("Введите ссылку на курс (или 'нет', если ссылки нет):")
    await state.set_state(AddCourse.link)


@router.message(AddCourse.link)
async def add_course_link(message: Message, state: FSMContext):
    """Получение ссылки на курс и сохранение"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Добавление курса отменено")
        return

    data = await state.get_data()
    link = None if message.text.lower() == "нет" else message.text

    # Создаем курс
    additional_data = {'link': link} if link else None
    course_id = await crud.create_resource(
        resource_type='course',
        title=data['title'],
        content=data['content'],
        additional_data=additional_data
    )

    # Логируем действие
    user = await crud.get_user_by_telegram_id(message.from_user.id)
    await crud.create_log(
        user['id'],
        'add_course',
        {'course_id': course_id, 'title': data['title']}
    )

    await state.clear()
    await message.answer(
        f"✅ Курс <b>{data['title']}</b> успешно добавлен!",
        parse_mode='HTML'
    )


# ========== ДОБАВЛЕНИЕ КОНКУРСОВ ==========

@router.message(F.text == "Добавить конкурс")
async def add_competition_start(message: Message, state: FSMContext):
    """Начало добавления конкурса"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user or not is_admin(user['role']):
        await message.answer("У вас нет прав администратора!")
        return

    await message.answer(
        "Введите название конкурса:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AddCompetition.title)


@router.message(AddCompetition.title)
async def add_competition_title(message: Message, state: FSMContext):
    """Получение названия конкурса"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Добавление конкурса отменено")
        return

    await state.update_data(title=message.text)
    await message.answer("Введите описание конкурса:")
    await state.set_state(AddCompetition.content)


@router.message(AddCompetition.content)
async def add_competition_content(message: Message, state: FSMContext):
    """Получение описания конкурса"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Добавление конкурса отменено")
        return

    await state.update_data(content=message.text)
    await message.answer("Введите дедлайн конкурса (например: 2025-12-31):")
    await state.set_state(AddCompetition.deadline)


@router.message(AddCompetition.deadline)
async def add_competition_deadline(message: Message, state: FSMContext):
    """Получение дедлайна конкурса"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Добавление конкурса отменено")
        return

    await state.update_data(deadline=message.text)
    await message.answer("Введите ссылку на конкурс (или 'нет', если ссылки нет):")
    await state.set_state(AddCompetition.link)


@router.message(AddCompetition.link)
async def add_competition_link(message: Message, state: FSMContext):
    """Получение ссылки на конкурс и сохранение"""
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Добавление конкурса отменено")
        return

    data = await state.get_data()
    link = None if message.text.lower() == "нет" else message.text

    # Создаем конкурс
    additional_data = {
        'deadline': data['deadline'],
        'link': link
    }
    competition_id = await crud.create_resource(
        resource_type='competition',
        title=data['title'],
        content=data['content'],
        additional_data=additional_data
    )

    # Логируем действие
    user = await crud.get_user_by_telegram_id(message.from_user.id)
    await crud.create_log(
        user['id'],
        'add_competition',
        {'competition_id': competition_id, 'title': data['title']}
    )

    await state.clear()
    await message.answer(
        f"✅ Конкурс <b>{data['title']}</b> успешно добавлен!",
        parse_mode='HTML'
    )


# ========== ЛОГИ ==========

@router.message(F.text == "Логи")
async def view_logs(message: Message):
    """Просмотр логов"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user or not is_admin(user['role']):
        await message.answer("У вас нет прав администратора!")
        return

    logs = await crud.get_logs(limit=20)

    if not logs:
        await message.answer("Логов пока нет.")
        return

    text = "<b>📋 Последние 20 логов:</b>\n\n"
    for log in logs:
        # Форматируем дату
        created_at = log['created_at'][:16] if log['created_at'] else ''

        # Форматируем действие
        action_text = {
            'add_course': '➕ Добавлен курс',
            'add_competition': '➕ Добавлен конкурс',
            'create_news': '📰 Создана новость',
            'create_contract': '📄 Создан договор',
            'verify_organization': '✅ Верифицирована организация',
            'reject_organization': '❌ Отклонена организация',
        }.get(log['action'], log['action'])

        text += f"<b>{created_at}</b>\n"
        text += f"👤 {log['full_name']} (@{log['username']})\n"
        text += f"📌 {action_text}\n"

        if log.get('details'):
            details_text = ", ".join([f"{k}: {v}" for k, v in log['details'].items()])
            text += f"ℹ️ {details_text}\n"

        text += "\n"

    # Разбиваем на части, если текст слишком длинный
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode='HTML')
    else:
        await message.answer(text, parse_mode='HTML')
