import aiosqlite
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

DATABASE_PATH = "bot.db"


async def init_db():
    """Инициализация базы данных и создание таблиц"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'organization',
                is_blocked INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица организаций
        await db.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                legal_form TEXT NOT NULL,
                activity_field TEXT,
                okved TEXT,
                inn TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                telegram TEXT NOT NULL,
                description TEXT NOT NULL,
                turnover TEXT NOT NULL,
                can_give TEXT NOT NULL,
                need TEXT NOT NULL,
                interaction_format TEXT NOT NULL,
                city TEXT,
                partnership_type TEXT NOT NULL,
                gdpr_consent INTEGER DEFAULT 1,
                verification_status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Таблица верификаций
        await db.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER UNIQUE NOT NULL,
                admin_id INTEGER,
                status TEXT DEFAULT 'pending',
                video_call_completed INTEGER DEFAULT 0,
                rejection_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                verified_at TEXT,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (admin_id) REFERENCES users(id)
            )
        """)

        # Таблица лайков
        await db.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_org_id INTEGER NOT NULL,
                to_org_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_org_id) REFERENCES organizations(id),
                FOREIGN KEY (to_org_id) REFERENCES organizations(id)
            )
        """)

        # Таблица матчей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org1_id INTEGER NOT NULL,
                org2_id INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (org1_id) REFERENCES organizations(id),
                FOREIGN KEY (org2_id) REFERENCES organizations(id)
            )
        """)

        # Таблица договоров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_org_id INTEGER NOT NULL,
                recipient_org_id INTEGER NOT NULL,
                contract_data TEXT NOT NULL,
                file_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_org_id) REFERENCES organizations(id),
                FOREIGN KEY (recipient_org_id) REFERENCES organizations(id)
            )
        """)

        # Таблица новостей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                media_ids TEXT,
                views_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            )
        """)

        # Таблица наставников
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mentors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                expertise TEXT NOT NULL,
                experience TEXT NOT NULL,
                contact_info TEXT NOT NULL,
                is_available INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Таблица ресурсов (конкурсы, курсы, FAQ)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                additional_data TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица логов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await db.commit()
        print("База данных инициализирована")


async def get_db():
    """Получить подключение к базе данных"""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


def dict_to_json(data: Dict) -> str:
    """Преобразовать словарь в JSON строку"""
    return json.dumps(data, ensure_ascii=False)


def json_to_dict(data: str) -> Dict:
    """Преобразовать JSON строку в словарь"""
    if not data:
        return {}
    return json.loads(data)
