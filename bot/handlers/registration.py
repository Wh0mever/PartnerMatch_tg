from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database import crud
from bot.states import RegistrationOrg, RegistrationMentor
from bot.keyboards.registration import (
    get_legal_form_keyboard, get_turnover_keyboard,
    get_partnership_options_keyboard, get_interaction_format_keyboard,
    get_partnership_type_keyboard, get_gdpr_keyboard
)
from bot.keyboards.main_menu import get_main_menu_keyboard
from config.config import settings

router = Router()


# ============= РЕГИСТРАЦИЯ ОРГАНИЗАЦИИ =============

@router.callback_query(F.data == "register_org")
async def start_org_registration(callback: CallbackQuery, state: FSMContext):
    """Начало регистрации организации"""
    await callback.message.edit_text(
        "<b>Регистрация организации</b>\n\n"
        "Пожалуйста, введите <b>название вашей организации</b>:"
    )
    await state.set_state(RegistrationOrg.name)
    await callback.answer()


@router.message(RegistrationOrg.name)
async def process_org_name(message: Message, state: FSMContext):
    """Обработка названия организации"""
    await state.update_data(name=message.text)
    await message.answer(
        f"Название: <b>{message.text}</b>\n\n"
        "Выберите юридическую форму:",
        reply_markup=get_legal_form_keyboard()
    )
    await state.set_state(RegistrationOrg.legal_form)


@router.callback_query(RegistrationOrg.legal_form, F.data.startswith("legal_form:"))
async def process_legal_form(callback: CallbackQuery, state: FSMContext):
    """Обработка юридической формы"""
    legal_form = callback.data.split(":")[1]
    await state.update_data(legal_form=legal_form)

    if legal_form == "Самозанятость":
        await callback.message.edit_text(
            f"Юридическая форма: <b>{legal_form}</b>\n\n"
            "Введите сферу вашей деятельности:"
        )
        await state.set_state(RegistrationOrg.activity_field_or_okved)
        await state.update_data(is_self_employed=True)
    else:
        await callback.message.edit_text(
            f"Юридическая форма: <b>{legal_form}</b>\n\n"
            "Введите ОКВЭД вашей организации:"
        )
        await state.set_state(RegistrationOrg.activity_field_or_okved)
        await state.update_data(is_self_employed=False)

    await callback.answer()


@router.message(RegistrationOrg.activity_field_or_okved)
async def process_activity_or_okved(message: Message, state: FSMContext):
    """Обработка сферы деятельности или ОКВЭД"""
    data = await state.get_data()
    is_self_employed = data.get("is_self_employed", False)

    # Проверка на заблокированные типы бизнеса
    text_lower = message.text.lower()
    is_blocked = any(keyword in text_lower for keyword in settings.BLOCKED_KEYWORDS)

    if is_blocked:
        await message.answer(
            "К сожалению, ваша деятельность относится к категории, "
            "которая не может быть зарегистрирована в системе.\n\n"
            "Причины:\n"
            "- Игорный бизнес\n"
            "- Алкогольный бизнес\n"
            "- Табачный бизнес\n"
            "- Деятельность, противоречащая законодательству РФ\n\n"
            "Для разблокировки обратитесь к администратору."
        )
        await state.clear()
        return

    if is_self_employed:
        await state.update_data(activity_field=message.text)
    else:
        await state.update_data(okved=message.text)

    await message.answer(
        f"{'Сфера деятельности' if is_self_employed else 'ОКВЭД'}: <b>{message.text}</b>\n\n"
        "Введите ИНН вашей организации (10 или 12 цифр):"
    )
    await state.set_state(RegistrationOrg.inn)


@router.message(RegistrationOrg.inn)
async def process_inn(message: Message, state: FSMContext):
    """Обработка ИНН"""
    inn = message.text.strip()

    # Проверка формата ИНН
    if not inn.isdigit() or len(inn) not in [10, 12]:
        await message.answer(
            "ИНН должен содержать 10 или 12 цифр. Попробуйте еще раз:"
        )
        return

    # Проверка уникальности ИНН
    existing_org = await crud.get_organization_by_inn(inn)
    if existing_org:
        await message.answer(
            "Организация с таким ИНН уже зарегистрирована в системе!"
        )
        await state.clear()
        return

    await state.update_data(inn=inn)
    await message.answer(
        f"ИНН: <b>{inn}</b>\n\n"
        "Введите контактный телефон (в формате +7XXXXXXXXXX):"
    )
    await state.set_state(RegistrationOrg.phone)


@router.message(RegistrationOrg.phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефона"""
    await state.update_data(phone=message.text)
    await message.answer(
        f"Телефон: <b>{message.text}</b>\n\n"
        "Введите email для связи:"
    )
    await state.set_state(RegistrationOrg.email)


@router.message(RegistrationOrg.email)
async def process_email(message: Message, state: FSMContext):
    """Обработка email"""
    await state.update_data(email=message.text)
    await message.answer(
        f"Email: <b>{message.text}</b>\n\n"
        "Введите Telegram для связи (например, @username):"
    )
    await state.set_state(RegistrationOrg.telegram)


@router.message(RegistrationOrg.telegram)
async def process_telegram(message: Message, state: FSMContext):
    """Обработка Telegram контакта"""
    await state.update_data(telegram_contact=message.text)
    await message.answer(
        f"Telegram: <b>{message.text}</b>\n\n"
        "Введите описание деятельности вашей организации:"
    )
    await state.set_state(RegistrationOrg.description)


@router.message(RegistrationOrg.description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания"""
    from config.config import settings

    # Проверка на запрещенные ключевые слова
    description_lower = message.text.lower()
    blocked = False
    for keyword in settings.BLOCKED_KEYWORDS:
        if keyword in description_lower:
            blocked = True
            break

    if blocked:
        await message.answer(
            "❌ <b>Регистрация отклонена</b>\n\n"
            "Ваша организация осуществляет деятельность, которая не подлежит регистрации "
            "на платформе согласно правилам:\n\n"
            "• Игорный бизнес\n"
            "• Алкогольная продукция\n"
            "• Табачная продукция\n"
            "• Деятельность, противоречащая законодательству РФ\n\n"
            "Для уточнения информации обратитесь в поддержку.",
            parse_mode='HTML'
        )
        await state.clear()
        return

    await state.update_data(description=message.text)
    await message.answer(
        "Описание сохранено.\n\n"
        "Выберите годовой оборот вашей компании:",
        reply_markup=get_turnover_keyboard()
    )
    await state.set_state(RegistrationOrg.turnover)


@router.callback_query(RegistrationOrg.turnover, F.data.startswith("turnover:"))
async def process_turnover(callback: CallbackQuery, state: FSMContext):
    """Обработка оборотов"""
    turnover = callback.data.split(":")[1]
    await state.update_data(turnover=turnover)
    await state.update_data(can_give_list=[])

    await callback.message.edit_text(
        f"Оборот: <b>{turnover}</b>\n\n"
        "Что ваша организация <b>МОЖЕТ ДАТЬ</b> партнёру?\n"
        "Выберите все подходящие варианты:",
        reply_markup=get_partnership_options_keyboard("can_give", [])
    )
    await state.set_state(RegistrationOrg.can_give)
    await callback.answer()


@router.callback_query(RegistrationOrg.can_give, F.data.startswith("can_give:"))
async def process_can_give(callback: CallbackQuery, state: FSMContext):
    """Обработка опций 'может дать'"""
    option = callback.data.split(":")[1]

    if option == "done":
        data = await state.get_data()
        can_give_list = data.get("can_give_list", [])

        if not can_give_list:
            await callback.answer("Выберите хотя бы один вариант!", show_alert=True)
            return

        await state.update_data(need_list=[])
        await callback.message.edit_text(
            "Что вашей организации <b>НУЖНО</b> от партнёра?\n"
            "Выберите все подходящие варианты:",
            reply_markup=get_partnership_options_keyboard("need", [])
        )
        await state.set_state(RegistrationOrg.need)

    elif option == "other":
        await callback.message.edit_text(
            "Введите свой вариант того, что вы можете дать:"
        )
        await state.set_state(RegistrationOrg.can_give_other)

    else:
        data = await state.get_data()
        can_give_list = data.get("can_give_list", [])

        if option in can_give_list:
            can_give_list.remove(option)
            await callback.answer(f"❌ {option}", show_alert=False)
        else:
            can_give_list.append(option)
            await callback.answer(f"✅ {option}", show_alert=False)

        await state.update_data(can_give_list=can_give_list)

        # Обновляем клавиатуру с галочками
        await callback.message.edit_reply_markup(
            reply_markup=get_partnership_options_keyboard("can_give", can_give_list)
        )

    await callback.answer()


@router.message(RegistrationOrg.can_give_other)
async def process_can_give_other(message: Message, state: FSMContext):
    """Обработка пользовательского варианта 'может дать'"""
    data = await state.get_data()
    can_give_list = data.get("can_give_list", [])
    can_give_list.append(message.text)
    await state.update_data(can_give_list=can_give_list)

    await message.answer(
        f"Добавлено: <b>{message.text}</b>\n\n"
        "Продолжайте выбирать или нажмите 'Готово':",
        reply_markup=get_partnership_options_keyboard("can_give", can_give_list)
    )
    await state.set_state(RegistrationOrg.can_give)


@router.callback_query(RegistrationOrg.need, F.data.startswith("need:"))
async def process_need(callback: CallbackQuery, state: FSMContext):
    """Обработка опций 'что нужно'"""
    option = callback.data.split(":")[1]

    if option == "done":
        data = await state.get_data()
        need_list = data.get("need_list", [])

        if not need_list:
            await callback.answer("Выберите хотя бы один вариант!", show_alert=True)
            return

        await callback.message.edit_text(
            "Выберите формат взаимодействия:",
            reply_markup=get_interaction_format_keyboard()
        )
        await state.set_state(RegistrationOrg.interaction_format)

    elif option == "other":
        await callback.message.edit_text(
            "Введите свой вариант того, что вам нужно:"
        )
        await state.set_state(RegistrationOrg.need_other)

    else:
        data = await state.get_data()
        need_list = data.get("need_list", [])

        if option in need_list:
            need_list.remove(option)
            await callback.answer(f"❌ {option}", show_alert=False)
        else:
            need_list.append(option)
            await callback.answer(f"✅ {option}", show_alert=False)

        await state.update_data(need_list=need_list)

        # Обновляем клавиатуру с галочками
        await callback.message.edit_reply_markup(
            reply_markup=get_partnership_options_keyboard("need", need_list)
        )

    await callback.answer()


@router.message(RegistrationOrg.need_other)
async def process_need_other(message: Message, state: FSMContext):
    """Обработка пользовательского варианта 'что нужно'"""
    data = await state.get_data()
    need_list = data.get("need_list", [])
    need_list.append(message.text)
    await state.update_data(need_list=need_list)

    await message.answer(
        f"Добавлено: <b>{message.text}</b>\n\n"
        "Продолжайте выбирать или нажмите 'Готово':",
        reply_markup=get_partnership_options_keyboard("need", need_list)
    )
    await state.set_state(RegistrationOrg.need)


@router.callback_query(RegistrationOrg.interaction_format, F.data.startswith("interaction:"))
async def process_interaction_format(callback: CallbackQuery, state: FSMContext):
    """Обработка формата взаимодействия"""
    format_type = callback.data.split(":")[1]
    await state.update_data(interaction_format=format_type)

    # Всегда спрашиваем город, независимо от формата
    await callback.message.edit_text(
        f"Формат: <b>{format_type}</b>\n\n"
        "Укажите город, в котором находится ваша организация:"
    )
    await state.set_state(RegistrationOrg.city)
    await callback.answer()


@router.message(RegistrationOrg.city)
async def process_city(message: Message, state: FSMContext):
    """Обработка города"""
    await state.update_data(city=message.text)
    await message.answer(
        f"Город: <b>{message.text}</b>\n\n"
        "Выберите тип партнёрства:",
        reply_markup=get_partnership_type_keyboard()
    )
    await state.set_state(RegistrationOrg.partnership_type)


@router.callback_query(RegistrationOrg.partnership_type, F.data.startswith("partnership_type:"))
async def process_partnership_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа партнёрства"""
    p_type = callback.data.split(":")[1]
    await state.update_data(partnership_type=p_type)

    await callback.message.edit_text(
        f"Тип партнёрства: <b>{p_type}</b>\n\n"
        "Подтвердите согласие на обработку персональных данных\n"
        "в соответствии с ФЗ-152:",
        reply_markup=get_gdpr_keyboard()
    )
    await state.set_state(RegistrationOrg.gdpr_consent)
    await callback.answer()


@router.callback_query(RegistrationOrg.gdpr_consent, F.data.startswith("gdpr:"))
async def process_gdpr(callback: CallbackQuery, state: FSMContext):
    """Обработка согласия на обработку данных"""
    consent = callback.data.split(":")[1]

    if consent == "decline":
        await callback.message.edit_text(
            "Без согласия на обработку персональных данных регистрация невозможна."
        )
        await state.clear()
        await callback.answer()
        return

    # Сохранение организации в базу данных
    data = await state.get_data()

    # Создаем пользователя
    user_id = await crud.create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
        role="organization"
    )

    # Создаем организацию
    org_id = await crud.create_organization(user_id, data)

    # Создаем запись верификации
    await crud.create_verification(org_id)

    # Логируем регистрацию
    await crud.create_log(user_id, "registration", {"type": "organization", "inn": data["inn"]})

    await callback.message.edit_text(
        "✅ <b>Регистрация завершена!</b>\n\n"
        "Ваша заявка отправлена на модерацию.\n"
        "Администратор проверит данные и проведёт видеозвонок для подтверждения.\n\n"
        "Вы получите уведомление о результатах проверки."
    )

    # Уведомляем owner'а и всех админов
    from aiogram import Bot
    from config.config import settings
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    bot = Bot(token=settings.BOT_TOKEN)

    # Подготавливаем строки для уведомлений
    can_give_str = ", ".join(data['can_give_list'])
    need_str = ", ".join(data['need_list'])

    # Подробное уведомление owner'у
    owner = await crud.get_owner()
    if owner:

        owner_msg = (
            f"📝 <b>НОВАЯ ЗАЯВКА НА РЕГИСТРАЦИЮ #{org_id}</b>\n\n"
            f"<b>Организация:</b> {data['name']}\n"
            f"<b>Юр. форма:</b> {data['legal_form']}\n"
            f"<b>ИНН:</b> {data['inn']}\n\n"
            f"<b>Контакты:</b>\n"
            f"📞 {data['phone']}\n"
            f"📧 {data['email']}\n"
            f"💬 {data['telegram_contact']}\n\n"
            f"<b>Оборот:</b> {data['turnover']}\n"
            f"<b>Формат:</b> {data['interaction_format']}"
        )

        if data.get('city'):
            owner_msg += f" ({data['city']})"

        owner_msg += (
            f"\n<b>Тип партнёрства:</b> {data['partnership_type']}\n\n"
            f"<b>Может дать:</b>\n{can_give_str}\n\n"
            f"<b>Нужно:</b>\n{need_str}\n\n"
            f"<b>Описание:</b>\n{data['description']}"
        )

        # Создаем инлайн-кнопки для модерации
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Одобрить", callback_data=f"verify_approve:{org_id}")
        builder.button(text="❌ Отклонить", callback_data=f"verify_reject:{org_id}")
        builder.adjust(2)

        try:
            await bot.send_message(
                owner['telegram_id'],
                owner_msg,
                parse_mode='HTML',
                reply_markup=builder.as_markup()
            )
        except:
            pass

    # Подробное уведомление всем админам
    admins = await crud.get_admins()
    for admin in admins:
        if admin['role'] != 'owner':  # owner уже получил подробное уведомление
            # Формируем подробное сообщение для админа (такое же как для owner)
            admin_msg = (
                f"📝 <b>НОВАЯ ЗАЯВКА НА РЕГИСТРАЦИЮ #{org_id}</b>\n\n"
                f"<b>Организация:</b> {data['name']}\n"
                f"<b>Юр. форма:</b> {data['legal_form']}\n"
                f"<b>ИНН:</b> {data['inn']}\n\n"
                f"<b>Контакты:</b>\n"
                f"📞 {data['phone']}\n"
                f"📧 {data['email']}\n"
                f"💬 {data['telegram_contact']}\n\n"
                f"<b>Оборот:</b> {data['turnover']}\n"
                f"<b>Формат:</b> {data['interaction_format']}"
            )

            if data.get('city'):
                admin_msg += f" ({data['city']})"

            admin_msg += (
                f"\n<b>Тип партнёрства:</b> {data['partnership_type']}\n\n"
                f"<b>Может дать:</b>\n{can_give_str}\n\n"
                f"<b>Нужно:</b>\n{need_str}\n\n"
                f"<b>Описание:</b>\n{data['description']}"
            )

            # Создаем кнопки для админов
            admin_builder = InlineKeyboardBuilder()
            admin_builder.button(text="✅ Одобрить", callback_data=f"verify_approve:{org_id}")
            admin_builder.button(text="❌ Отклонить", callback_data=f"verify_reject:{org_id}")
            admin_builder.adjust(2)

            try:
                await bot.send_message(
                    admin['telegram_id'],
                    admin_msg,
                    parse_mode='HTML',
                    reply_markup=admin_builder.as_markup()
                )
            except:
                pass
    await bot.session.close()

    await state.clear()
    await callback.answer()


# ============= РЕГИСТРАЦИЯ НАСТАВНИКА =============

@router.callback_query(F.data == "register_mentor")
async def start_mentor_registration(callback: CallbackQuery, state: FSMContext):
    """Начало регистрации наставника"""
    await callback.message.edit_text(
        "<b>Регистрация наставника</b>\n\n"
        "Введите ваше полное имя:"
    )
    await state.set_state(RegistrationMentor.name)
    await callback.answer()


@router.message(RegistrationMentor.name)
async def process_mentor_name(message: Message, state: FSMContext):
    """Обработка имени наставника"""
    await state.update_data(name=message.text)
    await message.answer(
        f"Имя: <b>{message.text}</b>\n\n"
        "Опишите вашу область экспертизы:"
    )
    await state.set_state(RegistrationMentor.expertise)


@router.message(RegistrationMentor.expertise)
async def process_mentor_expertise(message: Message, state: FSMContext):
    """Обработка экспертизы наставника"""
    await state.update_data(expertise=message.text)
    await message.answer(
        "Экспертиза сохранена.\n\n"
        "Опишите ваш опыт работы:"
    )
    await state.set_state(RegistrationMentor.experience)


@router.message(RegistrationMentor.experience)
async def process_mentor_experience(message: Message, state: FSMContext):
    """Обработка опыта наставника"""
    await state.update_data(experience=message.text)
    await message.answer(
        "Опыт сохранен.\n\n"
        "Введите ваши контактные данные для связи:"
    )
    await state.set_state(RegistrationMentor.contact_info)


@router.message(RegistrationMentor.contact_info)
async def process_mentor_contact(message: Message, state: FSMContext):
    """Завершение регистрации наставника"""
    data = await state.get_data()
    data['contact_info'] = message.text

    # Создаем пользователя
    user_id = await crud.create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        role="mentor"
    )

    # Создаем профиль наставника
    await crud.create_mentor(user_id, data)

    # Логируем регистрацию
    await crud.create_log(user_id, "registration", {"type": "mentor"})

    await message.answer(
        "✅ <b>Регистрация наставника завершена!</b>\n\n"
        "Теперь вы можете помогать другим участникам платформы.",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()
