import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "database.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Кэш результатов поиска по ID
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            query TEXT PRIMARY KEY,
            result TEXT NOT NULL,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Найденные мошенники (из каналов)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scammers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            username TEXT,
            mention TEXT,
            source_channel TEXT,
            message_text TEXT,
            message_id INTEGER,
            message_date TEXT,
            found_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Пользователи бота
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            checks_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Лог проверок
    cur.execute("""
        CREATE TABLE IF NOT EXISTS check_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            result_found INTEGER DEFAULT 0,
            checked_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Каналы-источники (управляются через админку)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            is_active INTEGER DEFAULT 1,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_parsed TEXT DEFAULT NULL,
            records_count INTEGER DEFAULT 0
        )
    """)

    # Вставляем дефолтные каналы из конфига если таблица пустая
    cur.execute("SELECT COUNT(*) FROM channels")
    if cur.fetchone()[0] == 0:
        from config import SCAM_CHANNELS
        for ch in SCAM_CHANNELS:
            cur.execute("""
                INSERT OR IGNORE INTO channels (username) VALUES (?)
            """, (ch.lower().strip("@"),))

    # Индексы для быстрого поиска
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scammers_id ON scammers(telegram_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scammers_username ON scammers(username)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scammers_mention ON scammers(mention)")

    # Ручные записи мошенников (добавленные админом)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS manual_scammers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT DEFAULT '',
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            description TEXT NOT NULL,
            media_file_ids TEXT DEFAULT '',
            added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_manual_id ON manual_scammers(telegram_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_manual_username ON manual_scammers(username)")

    # Суб-админы (урезанные права)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subadmins (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Подписки пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            telegram_id INTEGER PRIMARY KEY,
            expires_at TEXT NOT NULL,
            plan TEXT NOT NULL,
            activated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            activated_key TEXT DEFAULT ''
        )
    """)

    # Ключи активации
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sub_keys (
            key TEXT PRIMARY KEY,
            plan TEXT NOT NULL,
            days INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            used_by INTEGER DEFAULT NULL,
            used_at TEXT DEFAULT NULL,
            is_used INTEGER DEFAULT 0
        )
    """)

    # Кулдаун проверок для бесплатных
    cur.execute("""
        CREATE TABLE IF NOT EXISTS check_cooldown (
            telegram_id INTEGER PRIMARY KEY,
            last_check_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ==============================
# КЭШ
# ==============================

def get_cached(query: str) -> dict | None:
    from config import CACHE_TTL
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT result, cached_at FROM search_cache WHERE query = ?
    """, (query.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    # Проверяем TTL
    cached_at = datetime.fromisoformat(row["cached_at"])
    diff = (datetime.now() - cached_at).total_seconds()
    if diff > CACHE_TTL:
        return None
    return json.loads(row["result"])


def set_cache(query: str, result: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO search_cache (query, result, cached_at)
        VALUES (?, ?, ?)
    """, (query.lower().strip(), json.dumps(result, ensure_ascii=False), datetime.now().isoformat()))
    conn.commit()
    conn.close()


def clear_cache():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM search_cache")
    conn.commit()
    conn.close()


# ==============================
# МОШЕННИКИ
# ==============================

def save_scammer(telegram_id: str, username: str, mention: str,
                 source_channel: str, message_text: str,
                 message_id: int, message_date: str):
    conn = get_conn()
    cur = conn.cursor()
    # Проверяем дубликат
    cur.execute("""
        SELECT id FROM scammers
        WHERE source_channel = ? AND message_id = ?
    """, (source_channel, message_id))
    if cur.fetchone():
        conn.close()
        return
    cur.execute("""
        INSERT INTO scammers
        (telegram_id, username, mention, source_channel, message_text, message_id, message_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (telegram_id, username, mention, source_channel, message_text, message_id, message_date))
    conn.commit()
    conn.close()


def search_scammer_by_id(telegram_id: str) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM scammers
        WHERE telegram_id = ?
        ORDER BY found_at DESC
    """, (str(telegram_id),))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_scammer_by_username(username: str) -> list:
    conn = get_conn()
    cur = conn.cursor()
    uname = username.lower().strip("@")
    cur.execute("""
        SELECT * FROM scammers
        WHERE
            LOWER(username) = ?
            OR LOWER(username) LIKE ?
            OR LOWER(mention) LIKE ?
            OR LOWER(message_text) LIKE ?
        ORDER BY found_at DESC
        LIMIT 50
    """, (uname, f"%{uname}%", f"%{uname}%", f"%@{uname}%"))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_scammers_count() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT telegram_id) FROM scammers WHERE telegram_id != ''")
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_total_records() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM scammers")
    count = cur.fetchone()[0]
    conn.close()
    return count


# ==============================
# КАНАЛЫ
# ==============================

def get_channels(active_only: bool = False) -> list:
    conn = get_conn()
    cur = conn.cursor()
    if active_only:
        cur.execute("SELECT * FROM channels WHERE is_active = 1 ORDER BY added_at")
    else:
        cur.execute("SELECT * FROM channels ORDER BY added_at")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_channel(username: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO channels (username) VALUES (?)
        """, (username.lower().strip("@"),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def toggle_channel(channel_id: int) -> int:
    """Переключает активность канала. Возвращает новый статус."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT is_active FROM channels WHERE id = ?", (channel_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return -1
    new_status = 0 if row["is_active"] else 1
    cur.execute("UPDATE channels SET is_active = ? WHERE id = ?", (new_status, channel_id))
    conn.commit()
    conn.close()
    return new_status


def delete_channel(channel_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    conn.close()


def update_channel_parsed(username: str, records: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE channels SET last_parsed = CURRENT_TIMESTAMP, records_count = records_count + ?
        WHERE username = ?
    """, (records, username.lower().strip("@")))
    conn.commit()
    conn.close()


# ==============================
# РУЧНЫЕ ЗАПИСИ МОШЕННИКОВ
# ==============================

def add_manual_scammer(telegram_id: str, username: str, full_name: str,
                       description: str, media_file_ids: list, added_by: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO manual_scammers
        (telegram_id, username, full_name, description, media_file_ids, added_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        telegram_id.strip(),
        username.lower().strip("@"),
        full_name.strip(),
        description.strip(),
        json.dumps(media_file_ids),
        added_by
    ))
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id


def search_manual_by_id(telegram_id: str) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM manual_scammers WHERE telegram_id = ?
        ORDER BY added_at DESC
    """, (str(telegram_id).strip(),))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["media_file_ids"] = json.loads(d.get("media_file_ids") or "[]")
        result.append(d)
    return result


def search_manual_by_username(username: str) -> list:
    conn = get_conn()
    cur = conn.cursor()
    uname = username.lower().strip("@")
    cur.execute("""
        SELECT * FROM manual_scammers
        WHERE
            LOWER(username) = ?
            OR LOWER(username) LIKE ?
            OR LOWER(full_name) LIKE ?
            OR LOWER(description) LIKE ?
        ORDER BY added_at DESC
    """, (uname, f"%{uname}%", f"%{uname}%", f"%{uname}%"))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["media_file_ids"] = json.loads(d.get("media_file_ids") or "[]")
        result.append(d)
    return result


def get_all_manual_scammers(limit: int = 20, offset: int = 0) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM manual_scammers ORDER BY added_at DESC LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["media_file_ids"] = json.loads(d.get("media_file_ids") or "[]")
        result.append(d)
    return result


def delete_manual_scammer(record_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM manual_scammers WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def get_manual_count() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM manual_scammers")
    count = cur.fetchone()[0]
    conn.close()
    return count


# ==============================
# ПОЛЬЗОВАТЕЛИ
# ==============================

def register_user(telegram_id: int, username: str, first_name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (telegram_id, username, first_name)
        VALUES (?, ?, ?)
    """, (telegram_id, username or "", first_name or ""))
    conn.commit()
    conn.close()


def increment_user_checks(telegram_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users SET checks_count = checks_count + 1 WHERE telegram_id = ?
    """, (telegram_id,))
    conn.commit()
    conn.close()


def log_check(user_id: int, query: str, result_found: bool):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO check_log (user_id, query, result_found)
        VALUES (?, ?, ?)
    """, (user_id, query, 1 if result_found else 0))
    conn.commit()
    conn.close()


# ==============================
# СТАТИСТИКА
# ==============================

def get_stats() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM scammers")
    records = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT telegram_id) FROM scammers WHERE telegram_id != ''")
    unique_scammers = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM check_log")
    total_checks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM check_log WHERE result_found = 1")
    found_checks = cur.fetchone()[0]
    conn.close()
    return {
        "users": users,
        "records": records,
        "unique_scammers": unique_scammers,
        "total_checks": total_checks,
        "found_checks": found_checks,
    }


# ==============================
# СУБ-АДМИНЫ
# ==============================

def add_subadmin(telegram_id: int, username: str, first_name: str, added_by: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO subadmins (telegram_id, username, first_name, added_by)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, username or "", first_name or "", added_by))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_subadmin(telegram_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM subadmins WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()


def get_subadmins() -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subadmins ORDER BY added_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_subadmin(telegram_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM subadmins WHERE telegram_id = ?", (telegram_id,))
    result = cur.fetchone() is not None
    conn.close()
    return result


# ==============================
# ПОДПИСКИ
# ==============================

def has_active_subscription(telegram_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT expires_at FROM subscriptions
        WHERE telegram_id = ? AND expires_at > datetime('now')
    """, (telegram_id,))
    result = cur.fetchone() is not None
    conn.close()
    return result


def get_subscription(telegram_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT *, (expires_at > datetime('now')) as is_active
        FROM subscriptions WHERE telegram_id = ?
    """, (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def grant_subscription(telegram_id: int, days: int, plan: str, key: str = "") -> str:
    """Выдаёт подписку. Если уже есть активная — продлевает."""
    conn = get_conn()
    cur = conn.cursor()
    # Если уже есть активная — продлеваем от текущей даты истечения
    cur.execute("""
        SELECT expires_at FROM subscriptions
        WHERE telegram_id = ? AND expires_at > datetime('now')
    """, (telegram_id,))
    row = cur.fetchone()
    if row:
        base = row["expires_at"]
        new_expires = f"datetime('{base}', '+{days} days')"
        cur.execute(f"""
            UPDATE subscriptions
            SET expires_at = {new_expires}, plan = ?, activated_key = ?
            WHERE telegram_id = ?
        """, (plan, key, telegram_id))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO subscriptions (telegram_id, expires_at, plan, activated_key)
            VALUES (?, datetime('now', ?), ?, ?)
        """, (telegram_id, f"+{days} days", plan, key))
    conn.commit()
    # Получаем итоговую дату
    cur.execute("SELECT expires_at FROM subscriptions WHERE telegram_id = ?", (telegram_id,))
    expires = cur.fetchone()["expires_at"]
    conn.close()
    return expires


def revoke_subscription(telegram_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM subscriptions WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()


def get_active_subscriptions() -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, u.username, u.first_name
        FROM subscriptions s
        LEFT JOIN users u ON s.telegram_id = u.telegram_id
        WHERE s.expires_at > datetime('now')
        ORDER BY s.expires_at ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==============================
# КЛЮЧИ АКТИВАЦИИ
# ==============================

PLAN_LABELS = {
    "week": "1 неделя",
    "month": "1 месяц",
    "custom": "Кастомный",
}

PLAN_DAYS = {
    "week": 7,
    "month": 30,
}


def create_key(plan: str, days: int, created_by: int) -> str:
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits
    key = "OG-" + "".join(secrets.choice(alphabet) for _ in range(12))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sub_keys (key, plan, days, created_by)
        VALUES (?, ?, ?, ?)
    """, (key, plan, days, created_by))
    conn.commit()
    conn.close()
    return key


def activate_key(key: str, telegram_id: int) -> dict:
    """
    Активирует ключ. Возвращает dict с полями:
      ok: bool, reason: str, expires_at: str, plan: str, days: int
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sub_keys WHERE key = ?", (key.strip().upper(),))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"ok": False, "reason": "not_found"}
    if row["is_used"]:
        conn.close()
        return {"ok": False, "reason": "already_used"}
    # Помечаем ключ использованным
    cur.execute("""
        UPDATE sub_keys SET is_used = 1, used_by = ?, used_at = datetime('now')
        WHERE key = ?
    """, (telegram_id, key.strip().upper()))
    conn.commit()
    conn.close()
    # Выдаём подписку
    expires = grant_subscription(telegram_id, row["days"], row["plan"], key)
    return {
        "ok": True,
        "expires_at": expires,
        "plan": row["plan"],
        "days": row["days"],
    }


def get_keys(show_used: bool = False) -> list:
    conn = get_conn()
    cur = conn.cursor()
    if show_used:
        cur.execute("SELECT * FROM sub_keys ORDER BY created_at DESC LIMIT 30")
    else:
        cur.execute("SELECT * FROM sub_keys WHERE is_used = 0 ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_key(key: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM sub_keys WHERE key = ? AND is_used = 0", (key,))
    conn.commit()
    conn.close()


# ==============================
# КУЛДАУН
# ==============================

COOLDOWN_SECONDS = 30


def check_cooldown(telegram_id: int) -> int:
    """Возвращает секунд до следующей проверки. 0 — можно проверять."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT CAST((strftime('%s', 'now') - strftime('%s', last_check_at)) AS INTEGER) as diff
        FROM check_cooldown WHERE telegram_id = ?
    """, (telegram_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return 0
    diff = row["diff"] or 0
    remaining = COOLDOWN_SECONDS - diff
    return max(0, remaining)


def update_cooldown(telegram_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO check_cooldown (telegram_id, last_check_at)
        VALUES (?, datetime('now'))
    """, (telegram_id,))
    conn.commit()
    conn.close()


init_db()
