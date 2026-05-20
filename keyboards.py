from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(has_sub: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить по ID", callback_data="check_by_id"),
        InlineKeyboardButton(text="🔎 Проверить по @username", callback_data="check_by_username")
    )
    sub_label = "💎 Моя подписка" if has_sub else "💎 Купить подписку"
    builder.row(
        InlineKeyboardButton(text=sub_label, callback_data="subscription"),
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
    )
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def check_result_kb(query: str, has_results: bool, channel_links: list = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Новая проверка", callback_data="new_check"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")
    )
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="🔄 Обновить базу", callback_data="admin_parse")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить мошенника", callback_data="admin_add_scammer"),
        InlineKeyboardButton(text="📂 Мои записи", callback_data="admin_list_manual")
    )
    builder.row(
        InlineKeyboardButton(text="📡 Каналы-источники", callback_data="admin_channels"),
        InlineKeyboardButton(text="🔑 Суб-админы", callback_data="admin_subadmins")
    )
    builder.row(
        InlineKeyboardButton(text="🗝 Ключи подписки", callback_data="admin_keys"),
        InlineKeyboardButton(text="🗑 Очистить кэш", callback_data="admin_clear_cache")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Логи проверок", callback_data="admin_logs")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def parse_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, запустить", callback_data="admin_parse_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")
    )
    return builder.as_markup()


def skip_kb(callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=callback),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def done_media_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Готово, сохранить", callback_data="add_scammer_done"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def manual_record_kb(record_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить запись", callback_data=f"admin_del_manual:{record_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_list_manual")
    )
    return builder.as_markup()


def channels_list_kb(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = "✅" if ch["is_active"] else "❌"
        last = f" · {ch['last_parsed'][:10]}" if ch["last_parsed"] else ""
        builder.row(InlineKeyboardButton(
            text=f"{status} @{ch['username']}{last}",
            callback_data=f"ch_view:{ch['id']}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Добавить канал", callback_data="ch_add"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")
    )
    return builder.as_markup()


def channel_detail_kb(channel_id: int, is_active: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_label = "❌ Отключить" if is_active else "✅ Включить"
    builder.row(
        InlineKeyboardButton(text=toggle_label, callback_data=f"ch_toggle:{channel_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"ch_delete:{channel_id}")
    )
    builder.row(InlineKeyboardButton(text="◀️ К списку", callback_data="admin_channels"))
    return builder.as_markup()


def subadmin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить мошенника", callback_data="admin_add_scammer"),
        InlineKeyboardButton(text="📂 Мои записи", callback_data="admin_list_manual")
    )
    builder.row(
        InlineKeyboardButton(text="📡 Каналы-источники", callback_data="admin_channels"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def subadmins_list_kb(subadmins: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in subadmins:
        label = f"@{s['username']}" if s["username"] else f"ID {s['telegram_id']}"
        date = str(s["added_at"])[:10]
        builder.row(InlineKeyboardButton(
            text=f"👤 {label} [{date}]",
            callback_data=f"subadmin_del:{s['telegram_id']}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Добавить суб-админа", callback_data="subadmin_add"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")
    )
    return builder.as_markup()


# ==============================
# ПОДПИСКА
# ==============================

def subscription_kb(is_active: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_active:
        builder.row(InlineKeyboardButton(text="🔑 Ввести ключ активации", callback_data="sub_activate"))
    else:
        builder.row(InlineKeyboardButton(text="🔑 Продлить подписку (ввести ключ)", callback_data="sub_activate"))
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


# ==============================
# КЛЮЧИ ПОДПИСКИ (ADMIN)
# ==============================

def keys_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Создать ключ", callback_data="key_create"),
        InlineKeyboardButton(text="📋 Активные ключи", callback_data="keys_list")
    )
    builder.row(
        InlineKeyboardButton(text="🕓 Использованные", callback_data="keys_list_used"),
        InlineKeyboardButton(text="👤 Выдать вручную", callback_data="key_grant_manual")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Подписчики", callback_data="subs_list"),
        InlineKeyboardButton(text="🚫 Отозвать подписку", callback_data="key_revoke")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu"))
    return builder.as_markup()


def subs_list_kb(subs: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in subs:
        username = s.get("username") or ""
        first_name = s.get("first_name") or ""
        label = first_name or f"@{username}" if username else f"ID {s['telegram_id']}"
        if username and first_name:
            label = f"{first_name} @{username}"
        expires = str(s["expires_at"])[:10]
        plan = {"week": "7д", "month": "30д", "manual": "ручн.", "custom": f"{s.get('days', '?')}д"}.get(
            s["plan"], s["plan"]
        )
        builder.row(InlineKeyboardButton(
            text=f"💎 {label[:25]} · до {expires}",
            callback_data=f"sub_view:{s['telegram_id']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_keys"))
    return builder.as_markup()


def sub_detail_kb(telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Отозвать подписку", callback_data=f"sub_revoke:{telegram_id}"),
        InlineKeyboardButton(text="◀️ К списку", callback_data="subs_list")
    )
    return builder.as_markup()


def key_plans_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Неделя (7 дней) — 1$", callback_data="key_plan:week"),
        InlineKeyboardButton(text="🗓 Месяц (30 дней) — 4$", callback_data="key_plan:month")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Кастомный срок", callback_data="key_plan:custom"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_keys")
    )
    return builder.as_markup()


def key_custom_days_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="7 дней", callback_data="grant_days:7"),
        InlineKeyboardButton(text="30 дней", callback_data="grant_days:30"),
        InlineKeyboardButton(text="90 дней", callback_data="grant_days:90")
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def keys_list_kb(keys: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for k in keys[:15]:
        plan = {"week": "7д", "month": "30д", "custom": f"{k['days']}д"}.get(k["plan"], k["plan"])
        builder.row(InlineKeyboardButton(
            text=f"🗑 {k['key']} · {plan}",
            callback_data=f"key_delete:{k['key']}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_keys"))
    return builder.as_markup()

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить по ID", callback_data="check_by_id"),
        InlineKeyboardButton(text="🔎 Проверить по @username", callback_data="check_by_username")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
    )
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def check_result_kb(query: str, has_results: bool, channel_links: list = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Новая проверка", callback_data="new_check"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")
    )
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="🔄 Обновить базу", callback_data="admin_parse")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить мошенника", callback_data="admin_add_scammer"),
        InlineKeyboardButton(text="📂 Мои записи", callback_data="admin_list_manual")
    )
    builder.row(
        InlineKeyboardButton(text="📡 Каналы-источники", callback_data="admin_channels"),
        InlineKeyboardButton(text="🔑 Суб-админы", callback_data="admin_subadmins")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Очистить кэш", callback_data="admin_clear_cache"),
        InlineKeyboardButton(text="📋 Логи проверок", callback_data="admin_logs")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def parse_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, запустить", callback_data="admin_parse_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")
    )
    return builder.as_markup()


def skip_kb(callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=callback),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def done_media_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Готово, сохранить", callback_data="add_scammer_done"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def manual_record_kb(record_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить запись", callback_data=f"admin_del_manual:{record_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_list_manual")
    )
    return builder.as_markup()


def channels_list_kb(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status = "✅" if ch["is_active"] else "❌"
        last = f" · {ch['last_parsed'][:10]}" if ch["last_parsed"] else ""
        builder.row(InlineKeyboardButton(
            text=f"{status} @{ch['username']}{last}",
            callback_data=f"ch_view:{ch['id']}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Добавить канал", callback_data="ch_add"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")
    )
    return builder.as_markup()


def channel_detail_kb(channel_id: int, is_active: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_label = "❌ Отключить" if is_active else "✅ Включить"
    builder.row(
        InlineKeyboardButton(text=toggle_label, callback_data=f"ch_toggle:{channel_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"ch_delete:{channel_id}")
    )
    builder.row(InlineKeyboardButton(text="◀️ К списку", callback_data="admin_channels"))
    return builder.as_markup()


def subadmin_menu_kb() -> InlineKeyboardMarkup:
    """Урезанное меню для суб-админов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить мошенника", callback_data="admin_add_scammer"),
        InlineKeyboardButton(text="📂 Мои записи", callback_data="admin_list_manual")
    )
    builder.row(
        InlineKeyboardButton(text="📡 Каналы-источники", callback_data="admin_channels"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def subadmins_list_kb(subadmins: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in subadmins:
        label = f"@{s['username']}" if s["username"] else f"ID {s['telegram_id']}"
        date = str(s["added_at"])[:10]
        builder.row(InlineKeyboardButton(
            text=f"🔑 {label} [{date}]",
            callback_data=f"subadmin_del:{s['telegram_id']}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Добавить суб-админа", callback_data="subadmin_add"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")
    )
    return builder.as_markup()
