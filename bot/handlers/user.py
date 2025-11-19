"""Handlers для пользователей (организаций)"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton

from database import crud
from bot.states import CreateNews, CreateContract, ResourceCenterQuestion

router = Router()


# ========== РЕСУРСНЫЙ ЦЕНТР ==========

@router.message(F.text == "Ресурсный центр")
async def resource_center(message: Message):
    """Главное меню ресурсного центра"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    text = (
        "<b>📚 Ресурсный центр</b>\n\n"
        "Добро пожаловать в ресурсный центр! Здесь вы можете:\n\n"
        "• Задать вопрос специалистам\n"
        "• Получить консультацию по поиску партнёров\n"
        "• Узнать о доступных программах поддержки\n\n"
        "Выберите действие:"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="❓ Задать вопрос", callback_data="rc_ask_question")
    builder.button(text="📞 Контакты специалистов", callback_data="rc_contacts")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode='HTML')


@router.callback_query(F.data == "rc_ask_question")
async def rc_ask_question(callback: CallbackQuery, state: FSMContext):
    """Начать процесс задавания вопроса"""
    await callback.message.edit_text(
        "Напишите ваш вопрос специалистам ресурсного центра:"
    )
    await state.set_state(ResourceCenterQuestion.question)
    await callback.answer()


@router.message(ResourceCenterQuestion.question)
async def rc_question_received(message: Message, state: FSMContext):
    """Получение вопроса от пользователя"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    # Логируем вопрос
    await crud.create_log(
        user['id'],
        'resource_center_question',
        {'question': message.text[:100]}  # Первые 100 символов
    )

    # Отправляем администраторам
    admins = await crud.get_admins()
    from aiogram import Bot
    from config.config import settings

    bot = Bot(token=settings.BOT_TOKEN)
    for admin in admins:
        try:
            await bot.send_message(
                admin['telegram_id'],
                f"<b>❓ Новый вопрос в ресурсный центр</b>\n\n"
                f"От: {user['full_name']} (@{user['username']})\n\n"
                f"Вопрос:\n{message.text}",
                parse_mode='HTML'
            )
        except:
            pass
    await bot.session.close()

    await state.clear()
    await message.answer(
        "✅ Ваш вопрос отправлен специалистам ресурсного центра. "
        "Мы свяжемся с вами в ближайшее время!"
    )


@router.callback_query(F.data == "rc_contacts")
async def rc_contacts(callback: CallbackQuery):
    """Показать контакты специалистов"""
    text = (
        "<b>📞 Контакты специалистов ресурсного центра</b>\n\n"
        "Вы можете связаться с нашими специалистами:\n\n"
        "📧 Email: support@example.com\n"
        "📱 Телефон: +7 (XXX) XXX-XX-XX\n"
        "💬 Telegram: @resource_center_support\n\n"
        "Время работы: Пн-Пт, 9:00-18:00"
    )

    await callback.message.edit_text(text, parse_mode='HTML')
    await callback.answer()


# ========== НАСТАВНИК ==========

@router.message(F.text == "Наставник")
async def mentors_list(message: Message):
    """Список доступных наставников"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    mentors = await crud.get_all_mentors(is_available=True)

    if not mentors:
        await message.answer(
            "К сожалению, сейчас нет доступных наставников. "
            "Попробуйте позже!"
        )
        return

    text = "<b>👥 Доступные наставники</b>\n\n"

    for mentor in mentors:
        text += f"<b>{mentor['name']}</b>\n"
        text += f"Экспертиза: {mentor['expertise']}\n"
        text += f"Опыт: {mentor['experience']}\n"
        text += f"Контакт: {mentor['contact_info']}\n\n"
        text += "➖➖➖➖➖➖➖➖➖➖\n\n"

    await message.answer(text, parse_mode='HTML')


# ========== НОВОСТИ ==========

@router.message(F.text == "Новости")
async def news_menu(message: Message):
    """Меню новостей"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📰 Все новости", callback_data="news_all")
    builder.button(text="➕ Создать новость", callback_data="news_create")
    builder.button(text="📝 Мои новости", callback_data="news_my")
    builder.adjust(1)

    await message.answer(
        "<b>📰 Новости</b>\n\nВыберите действие:",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "news_all")
async def show_all_news(callback: CallbackQuery):
    """Показать все новости"""
    news_list = await crud.get_all_news(limit=10)

    if not news_list:
        await callback.message.edit_text("Новостей пока нет.")
        await callback.answer()
        return

    text = "<b>📰 Последние новости</b>\n\n"

    for news in news_list:
        text += f"<b>{news['title']}</b>\n"
        text += f"От: {news['org_name']}\n"
        text += f"{news['content'][:150]}...\n"
        text += f"👁 Просмотров: {news['views_count']}\n"
        text += f"📅 {news['created_at'][:10]}\n\n"
        text += "➖➖➖➖➖➖➖➖➖➖\n\n"

    # Разбиваем на части, если текст слишком длинный
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            if i == 0:
                await callback.message.edit_text(part, parse_mode='HTML')
            else:
                await callback.message.answer(part, parse_mode='HTML')
    else:
        await callback.message.edit_text(text, parse_mode='HTML')

    await callback.answer()


@router.callback_query(F.data == "news_create")
async def create_news_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания новости"""
    await callback.message.edit_text(
        "Введите заголовок новости:",
    )
    await state.set_state(CreateNews.title)
    await callback.answer()


@router.message(CreateNews.title)
async def create_news_title(message: Message, state: FSMContext):
    """Получение заголовка новости"""
    await state.update_data(title=message.text)
    await message.answer("Введите текст новости:")
    await state.set_state(CreateNews.content)


@router.message(CreateNews.content)
async def create_news_content(message: Message, state: FSMContext):
    """Получение текста новости"""
    await state.update_data(content=message.text)
    await message.answer(
        "Отправьте медиа-файлы (фото/видео) или напишите 'нет', если медиа не нужно:"
    )
    await state.set_state(CreateNews.media)


@router.message(CreateNews.media)
async def create_news_media(message: Message, state: FSMContext):
    """Получение медиа и создание новости"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)
    org = await crud.get_organization_by_user_id(user['id'])

    if not org:
        await message.answer("У вас нет организации!")
        await state.clear()
        return

    data = await state.get_data()

    # Создаем новость
    media_ids = None
    if message.text and message.text.lower() != 'нет':
        # Если это не текст, а медиа
        if message.photo:
            media_ids = [message.photo[-1].file_id]
        elif message.video:
            media_ids = [message.video.file_id]

    news_id = await crud.create_news(
        organization_id=org['id'],
        title=data['title'],
        content=data['content'],
        media_ids=media_ids
    )

    # Логируем действие
    await crud.create_log(
        user['id'],
        'create_news',
        {'news_id': news_id, 'title': data['title']}
    )

    await state.clear()
    await message.answer(
        f"✅ Новость <b>{data['title']}</b> успешно опубликована!",
        parse_mode='HTML'
    )


@router.callback_query(F.data == "news_my")
async def show_my_news(callback: CallbackQuery):
    """Показать новости моей организации"""
    user = await crud.get_user_by_telegram_id(callback.from_user.id)
    org = await crud.get_organization_by_user_id(user['id'])

    if not org:
        await callback.message.edit_text("У вас нет организации!")
        await callback.answer()
        return

    news_list = await crud.get_news_by_org(org['id'])

    if not news_list:
        await callback.message.edit_text("У вас пока нет опубликованных новостей.")
        await callback.answer()
        return

    text = "<b>📝 Мои новости</b>\n\n"

    for news in news_list:
        text += f"<b>{news['title']}</b>\n"
        text += f"{news['content'][:150]}...\n"
        text += f"👁 Просмотров: {news['views_count']}\n"
        text += f"📅 {news['created_at'][:10]}\n\n"
        text += "➖➖➖➖➖➖➖➖➖➖\n\n"

    await callback.message.edit_text(text, parse_mode='HTML')
    await callback.answer()


# ========== КОНКУРСЫ ==========

@router.message(F.text == "Конкурсы")
async def competitions_list(message: Message):
    """Список активных конкурсов"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    competitions = await crud.get_resources_by_type('competition', is_active=True)

    if not competitions:
        await message.answer("Активных конкурсов пока нет.")
        return

    text = "<b>🏆 Активные конкурсы</b>\n\n"

    for comp in competitions:
        text += f"<b>{comp['title']}</b>\n"
        text += f"{comp['content']}\n"

        if comp['additional_data']:
            if comp['additional_data'].get('deadline'):
                text += f"📅 Дедлайн: {comp['additional_data']['deadline']}\n"
            if comp['additional_data'].get('link'):
                text += f"🔗 Ссылка: {comp['additional_data']['link']}\n"

        text += "\n➖➖➖➖➖➖➖➖➖➖\n\n"

    # Разбиваем на части, если текст слишком длинный
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode='HTML')
    else:
        await message.answer(text, parse_mode='HTML')


# ========== ОБУЧЕНИЕ ==========

@router.message(F.text == "Обучение")
async def courses_list(message: Message):
    """Список доступных курсов"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    courses = await crud.get_resources_by_type('course', is_active=True)

    if not courses:
        await message.answer("Доступных курсов пока нет.")
        return

    text = "<b>📚 Доступные курсы</b>\n\n"

    for course in courses:
        text += f"<b>{course['title']}</b>\n"
        text += f"{course['content']}\n"

        if course['additional_data'] and course['additional_data'].get('link'):
            text += f"🔗 Ссылка: {course['additional_data']['link']}\n"

        text += "\n➖➖➖➖➖➖➖➖➖➖\n\n"

    # Разбиваем на части, если текст слишком длинный
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode='HTML')
    else:
        await message.answer(text, parse_mode='HTML')


# ========== ПРОФИЛЬ ==========

@router.message(F.text == "Профиль")
async def show_profile(message: Message):
    """Показать профиль организации"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    org = await crud.get_organization_by_user_id(user['id'])

    if not org:
        await message.answer("У вас нет организации!")
        return

    text = f"<b>🏢 Профиль организации</b>\n\n"
    text += f"Название: <b>{org['name']}</b>\n"
    text += f"Юридическая форма: {org['legal_form']}\n"
    text += f"ИНН: {org['inn']}\n"
    text += f"Телефон: {org['phone']}\n"
    text += f"Email: {org['email']}\n"
    text += f"Telegram: {org['telegram']}\n\n"
    text += f"<b>Описание:</b>\n{org['description']}\n\n"
    text += f"Оборот: {org['turnover']}\n"
    text += f"Город: {org.get('city', 'Не указан')}\n"
    text += f"Формат взаимодействия: {org['interaction_format']}\n"
    text += f"Тип партнёрства: {org['partnership_type']}\n\n"

    # Статус верификации
    status_emoji = {
        'pending': '⏳',
        'verified': '✅',
        'rejected': '❌'
    }
    text += f"{status_emoji.get(org['verification_status'], '')} Статус: {org['verification_status']}\n"

    await message.answer(text, parse_mode='HTML')


# ========== ДОКУМЕНТЫ ==========

@router.message(F.text == "Документы")
async def documents_menu(message: Message):
    """Меню документов"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    org = await crud.get_organization_by_user_id(user['id'])

    if not org:
        await message.answer("У вас нет организации!")
        return

    contracts = await crud.get_contracts_by_org(org['id'])

    if not contracts:
        await message.answer("У вас пока нет договоров.")
        return

    text = "<b>📄 Ваши договоры</b>\n\n"

    for contract in contracts:
        is_creator = contract['creator_org_id'] == org['id']
        other_party = contract['recipient_name'] if is_creator else contract['creator_name']

        text += f"<b>Договор #{contract['id']}</b>\n"
        text += f"С: {other_party}\n"
        text += f"Дата: {contract['created_at'][:10]}\n\n"
        text += "➖➖➖➖➖➖➖➖➖➖\n\n"

    await message.answer(text, parse_mode='HTML')


# ========== СОЗДАТЬ ДОГОВОР ==========

@router.message(F.text == "Создать договор")
async def create_contract_start(message: Message, state: FSMContext):
    """Начало создания договора"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Вы не зарегистрированы!")
        return

    org = await crud.get_organization_by_user_id(user['id'])

    if not org:
        await message.answer("У вас нет организации!")
        return

    # Получаем матчи
    from database.crud import get_db

    db = await get_db()
    async with db.execute("""
        SELECT DISTINCT o.id, o.name
        FROM matches m
        JOIN organizations o ON (
            CASE
                WHEN m.org1_id = ? THEN m.org2_id = o.id
                WHEN m.org2_id = ? THEN m.org1_id = o.id
            END
        )
        WHERE m.is_active = 1 AND (m.org1_id = ? OR m.org2_id = ?)
    """, (org['id'], org['id'], org['id'], org['id'])) as cursor:
        rows = await cursor.fetchall()
    await db.close()

    if not rows:
        await message.answer(
            "У вас пока нет подтверждённых партнёров (матчей). "
            "Найдите партнёров через поиск!"
        )
        return

    # Формируем кнопки с партнёрами
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.button(
            text=row[1],  # name
            callback_data=f"contract_partner:{row[0]}"  # id
        )
    builder.adjust(1)

    await message.answer(
        "<b>📄 Создание договора</b>\n\n"
        "Выберите партнёра, с которым хотите создать договор:",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )


@router.callback_query(F.data.startswith("contract_partner:"))
async def contract_select_partner(callback: CallbackQuery, state: FSMContext):
    """Выбор партнёра для договора"""
    partner_id = int(callback.data.split(":")[1])
    await state.update_data(partner_id=partner_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="🤝 Договор о партнёрстве", callback_data="contract_type:partnership")
    builder.button(text="📋 Договор о сотрудничестве", callback_data="contract_type:cooperation")
    builder.button(text="💼 Договор о предоставлении услуг", callback_data="contract_type:services")
    builder.adjust(1)

    await callback.message.edit_text(
        "Выберите тип договора:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("contract_type:"))
async def contract_select_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа договора"""
    contract_type = callback.data.split(":")[1]
    await state.update_data(contract_type=contract_type)

    await callback.message.edit_text(
        "Опишите условия договора (например: сумма, сроки, обязательства):"
    )
    await state.set_state(CreateContract.contract_details)
    await callback.answer()


@router.message(CreateContract.contract_details)
async def contract_create_final(message: Message, state: FSMContext):
    """Финальное создание договора"""
    user = await crud.get_user_by_telegram_id(message.from_user.id)
    org = await crud.get_organization_by_user_id(user['id'])

    data = await state.get_data()

    # Создаем договор
    contract_data = {
        'type': data['contract_type'],
        'details': message.text,
        'created_by': org['name']
    }

    contract_id = await crud.create_contract(
        creator_org_id=org['id'],
        recipient_org_id=data['partner_id'],
        contract_data=contract_data
    )

    # Логируем действие
    await crud.create_log(
        user['id'],
        'create_contract',
        {'contract_id': contract_id, 'type': data['contract_type']}
    )

    # Уведомляем партнёра
    partner_org = await crud.get_organization_by_id(data['partner_id'])
    partner_user = await crud.get_user_by_id(partner_org['user_id'])

    from aiogram import Bot
    from config.config import settings

    bot = Bot(token=settings.BOT_TOKEN)
    try:
        await bot.send_message(
            partner_user['telegram_id'],
            f"<b>📄 Новый договор</b>\n\n"
            f"Организация <b>{org['name']}</b> создала с вами договор.\n\n"
            f"Тип: {contract_data['type']}\n"
            f"Детали: {message.text}\n\n"
            f"Проверьте в разделе 'Документы'",
            parse_mode='HTML'
        )
    except:
        pass
    await bot.session.close()

    await state.clear()
    await message.answer(
        "✅ Договор успешно создан! Партнёр получил уведомление."
    )
