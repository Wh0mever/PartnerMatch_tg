"""CRUD операции для работы с базой данных"""
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from .database import get_db, dict_to_json, json_to_dict


# ========== USERS ==========

async def create_user(telegram_id: int, username: Optional[str], full_name: Optional[str], role: str = "organization") -> int:
    """Создать нового пользователя"""
    db = await get_db()
    async with db.execute(
        "INSERT INTO users (telegram_id, username, full_name, role) VALUES (?, ?, ?, ?)",
        (telegram_id, username, full_name, role)
    ) as cursor:
        user_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return user_id


async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """Получить пользователя по telegram_id"""
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Получить пользователя по ID"""
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def get_admins() -> List[Dict]:
    """Получить всех администраторов"""
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE role IN ('admin', 'owner')") as cursor:
        rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


async def get_owner() -> Optional[Dict]:
    """Получить owner'а"""
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE role = 'owner' LIMIT 1") as cursor:
        row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def update_user_role(telegram_id: int, new_role: str):
    """Обновить роль пользователя"""
    db = await get_db()
    await db.execute(
        "UPDATE users SET role = ? WHERE telegram_id = ?",
        (new_role, telegram_id)
    )
    await db.commit()
    await db.close()


# ========== ORGANIZATIONS ==========

async def create_organization(user_id: int, data: Dict) -> int:
    """Создать организацию"""
    db = await get_db()
    async with db.execute("""
        INSERT INTO organizations (
            user_id, name, legal_form, activity_field, okved, inn,
            phone, email, telegram, description, turnover,
            can_give, need, interaction_format, city, partnership_type,
            gdpr_consent, verification_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, data['name'], data['legal_form'],
        data.get('activity_field'), data.get('okved'), data['inn'],
        data['phone'], data['email'], data['telegram_contact'],
        data['description'], data['turnover'],
        dict_to_json({'options': data['can_give_list']}),
        dict_to_json({'options': data['need_list']}),
        data['interaction_format'], data.get('city'),
        data['partnership_type'], 1, 'pending'
    )) as cursor:
        org_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return org_id


async def get_organization_by_inn(inn: str) -> Optional[Dict]:
    """Получить организацию по ИНН"""
    db = await get_db()
    async with db.execute("SELECT * FROM organizations WHERE inn = ?", (inn,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    if row:
        org = dict(row)
        org['can_give'] = json_to_dict(org['can_give'])
        org['need'] = json_to_dict(org['need'])
        return org
    return None


async def get_organization_by_user_id(user_id: int) -> Optional[Dict]:
    """Получить организацию по user_id"""
    db = await get_db()
    async with db.execute("SELECT * FROM organizations WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    if row:
        org = dict(row)
        org['can_give'] = json_to_dict(org['can_give'])
        org['need'] = json_to_dict(org['need'])
        return org
    return None


async def get_organization_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """Получить организацию по telegram_id пользователя"""
    db = await get_db()
    async with db.execute("""
        SELECT o.* FROM organizations o
        JOIN users u ON o.user_id = u.id
        WHERE u.telegram_id = ?
    """, (telegram_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    if row:
        org = dict(row)
        org['can_give'] = json_to_dict(org['can_give'])
        org['need'] = json_to_dict(org['need'])
        return org
    return None


async def get_organization_by_id(org_id: int) -> Optional[Dict]:
    """Получить организацию по ID"""
    db = await get_db()
    async with db.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    if row:
        org = dict(row)
        org['can_give'] = json_to_dict(org['can_give'])
        org['need'] = json_to_dict(org['need'])
        return org
    return None


async def update_organization_status(org_id: int, status: str):
    """Обновить статус верификации организации"""
    db = await get_db()
    await db.execute(
        "UPDATE organizations SET verification_status = ? WHERE id = ?",
        (status, org_id)
    )
    await db.commit()
    await db.close()


async def get_verified_organizations(exclude_id: int, turnover: str) -> List[Dict]:
    """Получить верифицированные организации"""
    db = await get_db()
    async with db.execute("""
        SELECT * FROM organizations
        WHERE id != ? AND verification_status = 'verified' AND turnover = ?
    """, (exclude_id, turnover)) as cursor:
        rows = await cursor.fetchall()
    await db.close()

    orgs = []
    for row in rows:
        org = dict(row)
        org['can_give'] = json_to_dict(org['can_give'])
        org['need'] = json_to_dict(org['need'])
        orgs.append(org)
    return orgs


# ========== VERIFICATIONS ==========

async def create_verification(organization_id: int) -> int:
    """Создать запись верификации"""
    db = await get_db()
    async with db.execute(
        "INSERT INTO verifications (organization_id, status) VALUES (?, 'pending')",
        (organization_id,)
    ) as cursor:
        verification_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return verification_id


async def get_pending_verifications() -> List[Dict]:
    """Получить все заявки на проверку"""
    db = await get_db()
    async with db.execute("""
        SELECT v.*, o.* FROM verifications v
        JOIN organizations o ON v.organization_id = o.id
        WHERE v.status = 'pending'
    """) as cursor:
        rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


async def update_verification(verification_id: int, admin_id: int, status: str, reason: Optional[str] = None):
    """Обновить статус верификации"""
    db = await get_db()
    verified_at = datetime.utcnow().isoformat() if status == 'approved' else None
    await db.execute("""
        UPDATE verifications
        SET admin_id = ?, status = ?, rejection_reason = ?, verified_at = ?
        WHERE id = ?
    """, (admin_id, status, reason, verified_at, verification_id))
    await db.commit()
    await db.close()


async def get_verification_by_id(verification_id: int) -> Optional[Dict]:
    """Получить верификацию по ID"""
    db = await get_db()
    async with db.execute("SELECT * FROM verifications WHERE id = ?", (verification_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def approve_verification(organization_id: int, admin_id: int):
    """Одобрить верификацию организации"""
    db = await get_db()

    # Обновляем статус верификации
    verified_at = datetime.utcnow().isoformat()
    await db.execute("""
        UPDATE verifications
        SET admin_id = ?, status = 'approved', verified_at = ?
        WHERE organization_id = ?
    """, (admin_id, verified_at, organization_id))

    # Обновляем статус организации
    await db.execute("""
        UPDATE organizations
        SET verification_status = 'verified'
        WHERE id = ?
    """, (organization_id,))

    await db.commit()
    await db.close()


async def reject_verification(organization_id: int, admin_id: int, reason: str):
    """Отклонить верификацию организации"""
    db = await get_db()

    # Обновляем статус верификации
    await db.execute("""
        UPDATE verifications
        SET admin_id = ?, status = 'rejected', rejection_reason = ?
        WHERE organization_id = ?
    """, (admin_id, reason, organization_id))

    # Обновляем статус организации
    await db.execute("""
        UPDATE organizations
        SET verification_status = 'rejected'
        WHERE id = ?
    """, (organization_id,))

    await db.commit()
    await db.close()


# ========== LIKES ==========

async def create_like(from_org_id: int, to_org_id: int):
    """Создать лайк"""
    db = await get_db()
    await db.execute(
        "INSERT INTO likes (from_org_id, to_org_id) VALUES (?, ?)",
        (from_org_id, to_org_id)
    )
    await db.commit()
    await db.close()


async def check_mutual_like(org1_id: int, org2_id: int) -> bool:
    """Проверить взаимный лайк"""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM likes WHERE from_org_id = ? AND to_org_id = ?",
        (org2_id, org1_id)
    ) as cursor:
        row = await cursor.fetchone()
    await db.close()
    return row is not None


async def get_liked_org_ids(from_org_id: int) -> List[int]:
    """Получить ID организаций, которым уже поставили лайк"""
    db = await get_db()
    async with db.execute(
        "SELECT to_org_id FROM likes WHERE from_org_id = ?",
        (from_org_id,)
    ) as cursor:
        rows = await cursor.fetchall()
    await db.close()
    return [row[0] for row in rows]


# ========== MATCHES ==========

async def create_match(org1_id: int, org2_id: int):
    """Создать матч"""
    db = await get_db()
    await db.execute(
        "INSERT INTO matches (org1_id, org2_id) VALUES (?, ?)",
        (org1_id, org2_id)
    )
    await db.commit()
    await db.close()


async def get_matches_count() -> int:
    """Получить количество матчей"""
    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM matches") as cursor:
        row = await cursor.fetchone()
    await db.close()
    return row[0] if row else 0


# ========== MENTORS ==========

async def create_mentor(user_id: int, data: Dict) -> int:
    """Создать наставника"""
    db = await get_db()
    async with db.execute("""
        INSERT INTO mentors (user_id, name, expertise, experience, contact_info)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, data['name'], data['expertise'], data['experience'], data['contact_info'])) as cursor:
        mentor_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return mentor_id


# ========== LOGS ==========

async def create_log(user_id: int, action: str, details: Optional[Dict] = None):
    """Создать лог"""
    db = await get_db()
    details_json = dict_to_json(details) if details else None
    await db.execute(
        "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, action, details_json)
    )
    await db.commit()
    await db.close()


# ========== STATISTICS ==========

async def get_statistics() -> Dict:
    """Получить статистику"""
    db = await get_db()

    async with db.execute("SELECT COUNT(*) FROM users") as cursor:
        total_users = (await cursor.fetchone())[0]

    async with db.execute("SELECT COUNT(*) FROM organizations") as cursor:
        total_orgs = (await cursor.fetchone())[0]

    async with db.execute("SELECT COUNT(*) FROM organizations WHERE verification_status = 'verified'") as cursor:
        verified_orgs = (await cursor.fetchone())[0]

    async with db.execute("SELECT COUNT(*) FROM organizations WHERE verification_status = 'pending'") as cursor:
        pending_orgs = (await cursor.fetchone())[0]

    async with db.execute("SELECT COUNT(*) FROM matches") as cursor:
        total_matches = (await cursor.fetchone())[0]

    await db.close()

    return {
        'total_users': total_users,
        'total_orgs': total_orgs,
        'verified_orgs': verified_orgs,
        'pending_orgs': pending_orgs,
        'total_matches': total_matches
    }


# ========== RESOURCES (COURSES & COMPETITIONS) ==========

async def create_resource(resource_type: str, title: str, content: str, additional_data: Optional[Dict] = None) -> int:
    """Создать ресурс (курс или конкурс)"""
    db = await get_db()
    data_json = dict_to_json(additional_data) if additional_data else None
    async with db.execute("""
        INSERT INTO resources (type, title, content, additional_data)
        VALUES (?, ?, ?, ?)
    """, (resource_type, title, content, data_json)) as cursor:
        resource_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return resource_id


async def get_resources_by_type(resource_type: str, is_active: bool = True) -> List[Dict]:
    """Получить ресурсы по типу"""
    db = await get_db()
    async with db.execute("""
        SELECT * FROM resources
        WHERE type = ? AND is_active = ?
        ORDER BY created_at DESC
    """, (resource_type, 1 if is_active else 0)) as cursor:
        rows = await cursor.fetchall()
    await db.close()

    resources = []
    for row in rows:
        res = dict(row)
        if res['additional_data']:
            res['additional_data'] = json_to_dict(res['additional_data'])
        resources.append(res)
    return resources


async def get_resource_by_id(resource_id: int) -> Optional[Dict]:
    """Получить ресурс по ID"""
    db = await get_db()
    async with db.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    if row:
        res = dict(row)
        if res['additional_data']:
            res['additional_data'] = json_to_dict(res['additional_data'])
        return res
    return None


async def update_resource(resource_id: int, **kwargs):
    """Обновить ресурс"""
    db = await get_db()
    updates = []
    values = []

    for key, value in kwargs.items():
        if key in ['title', 'content', 'is_active']:
            updates.append(f"{key} = ?")
            values.append(value)
        elif key == 'additional_data' and value is not None:
            updates.append("additional_data = ?")
            values.append(dict_to_json(value))

    if updates:
        values.append(datetime.utcnow().isoformat())
        values.append(resource_id)
        query = f"UPDATE resources SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
        await db.execute(query, values)
        await db.commit()

    await db.close()


async def delete_resource(resource_id: int):
    """Удалить ресурс (мягкое удаление)"""
    db = await get_db()
    await db.execute("UPDATE resources SET is_active = 0 WHERE id = ?", (resource_id,))
    await db.commit()
    await db.close()


# ========== NEWS ==========

async def create_news(organization_id: int, title: str, content: str, media_ids: Optional[List[str]] = None) -> int:
    """Создать новость"""
    db = await get_db()
    media_json = dict_to_json({'ids': media_ids}) if media_ids else None
    async with db.execute("""
        INSERT INTO news (organization_id, title, content, media_ids)
        VALUES (?, ?, ?, ?)
    """, (organization_id, title, content, media_json)) as cursor:
        news_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return news_id


async def get_all_news(limit: int = 50) -> List[Dict]:
    """Получить все новости"""
    db = await get_db()
    async with db.execute("""
        SELECT n.*, o.name as org_name
        FROM news n
        JOIN organizations o ON n.organization_id = o.id
        ORDER BY n.created_at DESC
        LIMIT ?
    """, (limit,)) as cursor:
        rows = await cursor.fetchall()
    await db.close()

    news_list = []
    for row in rows:
        news = dict(row)
        if news['media_ids']:
            news['media_ids'] = json_to_dict(news['media_ids']).get('ids', [])
        news_list.append(news)
    return news_list


async def get_news_by_org(organization_id: int) -> List[Dict]:
    """Получить новости организации"""
    db = await get_db()
    async with db.execute("""
        SELECT * FROM news
        WHERE organization_id = ?
        ORDER BY created_at DESC
    """, (organization_id,)) as cursor:
        rows = await cursor.fetchall()
    await db.close()

    news_list = []
    for row in rows:
        news = dict(row)
        if news['media_ids']:
            news['media_ids'] = json_to_dict(news['media_ids']).get('ids', [])
        news_list.append(news)
    return news_list


async def increment_news_views(news_id: int):
    """Увеличить счетчик просмотров новости"""
    db = await get_db()
    await db.execute("UPDATE news SET views_count = views_count + 1 WHERE id = ?", (news_id,))
    await db.commit()
    await db.close()


# ========== CONTRACTS ==========

async def create_contract(creator_org_id: int, recipient_org_id: int, contract_data: Dict, file_id: Optional[str] = None) -> int:
    """Создать договор"""
    db = await get_db()
    data_json = dict_to_json(contract_data)
    async with db.execute("""
        INSERT INTO contracts (creator_org_id, recipient_org_id, contract_data, file_id)
        VALUES (?, ?, ?, ?)
    """, (creator_org_id, recipient_org_id, data_json, file_id)) as cursor:
        contract_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return contract_id


async def get_contracts_by_org(organization_id: int) -> List[Dict]:
    """Получить договоры организации"""
    db = await get_db()
    async with db.execute("""
        SELECT c.*,
               o1.name as creator_name,
               o2.name as recipient_name
        FROM contracts c
        JOIN organizations o1 ON c.creator_org_id = o1.id
        JOIN organizations o2 ON c.recipient_org_id = o2.id
        WHERE c.creator_org_id = ? OR c.recipient_org_id = ?
        ORDER BY c.created_at DESC
    """, (organization_id, organization_id)) as cursor:
        rows = await cursor.fetchall()
    await db.close()

    contracts = []
    for row in rows:
        contract = dict(row)
        contract['contract_data'] = json_to_dict(contract['contract_data'])
        contracts.append(contract)
    return contracts


async def get_contract_by_id(contract_id: int) -> Optional[Dict]:
    """Получить договор по ID"""
    db = await get_db()
    async with db.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    if row:
        contract = dict(row)
        contract['contract_data'] = json_to_dict(contract['contract_data'])
        return contract
    return None


# ========== MENTORS ==========

async def get_all_mentors(is_available: bool = True) -> List[Dict]:
    """Получить всех наставников"""
    db = await get_db()
    async with db.execute("""
        SELECT * FROM mentors
        WHERE is_available = ?
        ORDER BY created_at DESC
    """, (1 if is_available else 0,)) as cursor:
        rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


async def get_mentor_by_user_id(user_id: int) -> Optional[Dict]:
    """Получить наставника по user_id"""
    db = await get_db()
    async with db.execute("SELECT * FROM mentors WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def update_mentor_availability(user_id: int, is_available: bool):
    """Обновить доступность наставника"""
    db = await get_db()
    await db.execute(
        "UPDATE mentors SET is_available = ? WHERE user_id = ?",
        (1 if is_available else 0, user_id)
    )
    await db.commit()
    await db.close()


# ========== LOGS ==========

async def get_logs(limit: int = 100, user_id: Optional[int] = None) -> List[Dict]:
    """Получить логи"""
    db = await get_db()

    if user_id:
        query = """
            SELECT l.*, u.username, u.full_name
            FROM logs l
            JOIN users u ON l.user_id = u.id
            WHERE l.user_id = ?
            ORDER BY l.created_at DESC
            LIMIT ?
        """
        params = (user_id, limit)
    else:
        query = """
            SELECT l.*, u.username, u.full_name
            FROM logs l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT ?
        """
        params = (limit,)

    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
    await db.close()

    logs = []
    for row in rows:
        log = dict(row)
        if log['details']:
            log['details'] = json_to_dict(log['details'])
        logs.append(log)
    return logs
