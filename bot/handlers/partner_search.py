from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import crud

router = Router()


def format_organization_card(org: dict) -> str:
    """Форматирование карточки организации"""
    can_give = ", ".join(org['can_give'].get("options", []))
    need = ", ".join(org['need'].get("options", []))

    card = f"<b>{org['name']}</b>\n\n"
    card += f"📋 Юр. форма: {org['legal_form']}\n"
    card += f"💰 Оборот: {org['turnover']}\n"
    card += f"📍 Формат: {org['interaction_format']}"

    if org.get('city'):
        card += f" ({org['city']})"

    card += f"\n🤝 Тип: {org['partnership_type']}\n\n"
    card += f"<b>Может дать:</b>\n{can_give}\n\n"
    card += f"<b>Нужно:</b>\n{need}\n\n"
    card += f"<b>Описание:</b>\n{org['description']}"

    return card


@router.message(F.text == "Найти партнёра")
async def start_partner_search(message: Message):
    """Начало поиска партнеров"""
    org = await crud.get_organization_by_telegram_id(message.from_user.id)

    if not org:
        await message.answer("Вы не зарегистрированы как организация!")
        return

    if org['verification_status'] != "verified":
        await message.answer(
            "Ваша организация еще не верифицирована.\n"
            f"Статус: <b>{org['verification_status']}</b>"
        )
        return

    # Получаем всех верифицированных партнеров
    partners = await crud.get_verified_organizations(org['id'], org['turnover'])

    # Получаем ID тех, кому уже поставили лайк
    liked_ids = await crud.get_liked_org_ids(org['id'])

    # Фильтруем
    partners = [p for p in partners if p['id'] not in liked_ids]

    if not partners:
        await message.answer(
            "К сожалению, подходящих партнеров пока нет.\n"
            "Попробуйте позже!"
        )
        return

    # Показываем первого партнера
    partner = partners[0]
    card = format_organization_card(partner)

    builder = InlineKeyboardBuilder()
    builder.button(text="❤️ Интересно", callback_data=f"like:{partner['id']}")
    builder.button(text="👎 Не интересно", callback_data=f"dislike:{partner['id']}")
    builder.adjust(2)

    await message.answer(card, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("like:"))
async def process_like(callback: CallbackQuery):
    """Обработка лайка"""
    partner_id = int(callback.data.split(":")[1])
    org = await crud.get_organization_by_telegram_id(callback.from_user.id)

    # Создаем лайк
    await crud.create_like(org['id'], partner_id)

    # Проверяем взаимный лайк
    mutual = await crud.check_mutual_like(org['id'], partner_id)

    if mutual:
        # Создаем матч
        await crud.create_match(org['id'], partner_id)

        # Логируем матч
        user = await crud.get_user_by_telegram_id(callback.from_user.id)
        await crud.create_log(user['id'], "match", {"partner_id": partner_id})

        # Получаем данные партнера
        partner_org = await crud.get_organization_by_id(partner_id)

        await callback.message.edit_text(
            "🎉 <b>Это матч!</b>\n\n"
            f"Вы понравились друг другу с организацией <b>{partner_org['name']}</b>!\n\n"
            "Контакты партнера:\n"
            f"📞 Телефон: {partner_org['phone']}\n"
            f"📧 Email: {partner_org['email']}\n"
            f"💬 Telegram: {partner_org['telegram']}\n\n"
            "Свяжитесь с ними для обсуждения сотрудничества!"
        )

        # Уведомляем партнера
        from aiogram import Bot
        from config.config import settings
        bot = Bot(token=settings.BOT_TOKEN)

        partner_user = await crud.get_user_by_id(partner_org['user_id'])

        try:
            await bot.send_message(
                partner_user['telegram_id'],
                f"🎉 <b>Это матч!</b>\n\n"
                f"Вы понравились друг другу с организацией <b>{org['name']}</b>!\n\n"
                "Контакты партнера:\n"
                f"📞 Телефон: {org['phone']}\n"
                f"📧 Email: {org['email']}\n"
                f"💬 Telegram: {org['telegram']}"
            )
        except:
            pass
        await bot.session.close()

    else:
        # Логируем лайк
        user = await crud.get_user_by_telegram_id(callback.from_user.id)
        await crud.create_log(user['id'], "like", {"partner_id": partner_id})

        await callback.message.edit_text(
            "Лайк отправлен! ❤️\n\n"
            "Если организация тоже поставит вам лайк, вы получите уведомление."
        )

    await callback.answer()


@router.callback_query(F.data.startswith("dislike:"))
async def process_dislike(callback: CallbackQuery):
    """Обработка дизлайка"""
    await callback.message.delete()
    await callback.answer("Пропущено")
