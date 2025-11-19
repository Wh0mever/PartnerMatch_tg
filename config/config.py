class Settings:
    """Настройки приложения"""

    # Telegram Bot
    BOT_TOKEN: str = "8321718826:AAEs4I-pXAl0c1AmDAFzBw23HHKcR5oTgYA"
    OWNER_ID: int = 1914567632

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./bot.db"

    # Blocked business types
    BLOCKED_KEYWORDS = [
        "игорн", "казино", "ставк", "букмекер",
        "алкоголь", "водка", "пиво", "вино",
        "табак", "сигарет", "табачн"
    ]

    # Partnership options
    CAN_GIVE_OPTIONS = [
        "Финансирование", "Информационное", "Кадровое", "Идейное",
        "Площадка", "Совместный брендинг", "Кросс-продвижение",
        "Мероприятия", "Совместный контент", "Спонсорство",
        "Партнёрская программа"
    ]

    NEED_OPTIONS = CAN_GIVE_OPTIONS.copy()

    # Legal forms
    LEGAL_FORMS = [
        "Самозанятость", "ИП", "ООО", "ПАО",
        "Образовательная организация", "Иное"
    ]

    # Turnover ranges
    TURNOVER_RANGES = [
        "До 3 млн", "4-10 млн", "11-20 млн", "21+ млн"
    ]

    # Interaction formats
    INTERACTION_FORMATS = ["Очно", "Дистанционно"]

    # Partnership types
    PARTNERSHIP_TYPES = ["Постоянное", "Разовое"]


settings = Settings()
