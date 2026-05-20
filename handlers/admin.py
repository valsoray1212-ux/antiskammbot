import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS, SCAM_CHANNELS
from keyboards import (
    admin_menu_kb, subadmin_menu_kb, back_to_main_kb,
    parse_confirm_kb, channels_list_kb, channel_detail_kb,
    cancel_kb, subadmins_list_kb
)

router = Router()
logger = logging.getLogger(__name__)


# ==============================
# ФИЛЬТРЫ
# ==============================

class IsAnyAdmin(BaseFilter):
    """Главный админ ИЛИ суб-админ."""
    async def __call__(self, event) -> bool:
        uid = getattr(getattr(event, "from_user", None), "id", None)
        if uid in ADMIN_IDS:
            return True
        return db.is_subadmin(uid)


def is_owner(uid: int) -> bool:
    return uid in ADMIN_IDS


# ==============================
# FSM СОСТОЯНИЯ
# ==============================

class ChannelStates(StatesGroup):
    waiting_username = State()


class SubadminStates(StatesGroup):
    waiting_id = State()


router.message.filter(IsAnyAdmin())
router.callback_query.filter(IsAnyAdmin())


# ==============================
# ВХОД В ПАНЕЛЬ
# ==============================

@router.message(Command("admin"))
async def admin_panel(message: Message):
    uid = message.from_user.id
    stats = db.get_stats()

    if is_owner(uid):
        subadmins = db.get_subadmins()
        text = (
            "⚙️ <b>Панель администратора</b>\n"
            "<b>OpusGuru Anti-Scam</b>\n\n"
            f"👥 Пользователей: <b>{stats['users']:,}</b>\n"
            f"🗃 Записей в базе: <b>{stats['records']:,}</b>\n"
            f"👤 Уникальных мошенников: <b>{stats['unique_scammers']:,}</b>\n"
            f"🔍 Всего проверок: <b>{stats['total_checks']:,}</b>\n"
            f"🚨 С совпадениями: <b>{stats['found_checks']:,}</b>\n\n"
            f"🔑 Суб-админов: <b>{len(subadmins)}</b>"
        )
        await message.answer(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    else:
        text = (
            "🔧 <b>Панель модератора</b>\n"
            "<b>OpusGuru Anti-Scam</b>\n\n"
            f"🗃 Записей в базе: <b>{stats['records']:,}</b>\n"
            f"🔍 Всего проверок: <b>{stats['total_checks']:,}</b>\n"
        )
        await message.answer(text, reply_markup=subadmin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin_menu")
async def back_to_admin(call: CallbackQuery):
    uid = call.from_user.id
    stats = db.get_stats()
    if is_owner(uid):
        text = (
            "⚙️ <b>Панель администратора</b>\n\n"
            f"👥 Пользователей: <b>{stats['users']:,}</b>\n"
            f"🗃 Записей: <b>{stats['records']:,}</b>\n"
            f"🔍 Проверок: <b>{stats['total_checks']:,}</b>\n"
        )
        await call.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    else:
        text = (
            "🔧 <b>Панель модератора</b>\n\n"
            f"🗃 Записей: <b>{stats['records']:,}</b>\n"
            f"🔍 Проверок: <b>{stats['total_checks']:,}</b>\n"
        )
        await call.message.edit_text(text, reply_markup=subadmin_menu_kb(), parse_mode="HTML")


# ==============================
# ТОЛЬКО ГЛАВНЫЙ АДМИН
# ==============================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔️ Только для главного администратора", show_alert=True)
        return
    stats = db.get_stats()
    text = (
        "📊 <b>Полная статистика</b>\n\n"
        f"👥 Пользователей бота: <b>{stats['users']:,}</b>\n"
        f"🗃 Всего записей: <b>{stats['records']:,}</b>\n"
        f"👤 Уникальных мошенников: <b>{stats['unique_scammers']:,}</b>\n"
        f"🔍 Всего проверок: <b>{stats['total_checks']:,}</b>\n"
        f"🚨 Найдено совпадений: <b>{stats['found_checks']:,}</b>\n"
        f"✅ Чистых проверок: <b>{stats['total_checks'] - stats['found_checks']:,}</b>\n"
    )
    await call.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin_parse")
async def admin_parse_confirm(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔️ Только для главного администратора", show_alert=True)
        return
    channels = db.get_channels(active_only=True)
    total = db.get_total_records()
    await call.message.edit_text(
        "🔄 <b>Обновление базы мошенников</b>\n\n"
        f"Сейчас в базе: <b>{total:,}</b> записей\n\n"
        f"Активных каналов: <b>{len(channels)}</b>\n"
        + "\n".join([f"   • @{c['username']}" for c in channels]) +
        "\n\n⚠️ Это займёт несколько минут. Запустить?",
        reply_markup=parse_confirm_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_parse_confirm")
async def run_parse(call: CallbackQuery):
    await call.message.edit_text(
        "⏳ <b>Парсинг запущен...</b>\n\n"
        "Обрабатываю каналы, это займёт несколько минут.\n"
        "Уведомлю когда закончу.",
        parse_mode="HTML"
    )
    asyncio.create_task(_run_parse_task(call))


async def _run_parse_task(call: CallbackQuery):
    try:
        from parser import parse_all_channels
        results = await parse_all_channels()
        total = db.get_total_records()
        result_lines = "\n".join([f"   @{ch}: +{cnt} записей" for ch, cnt in results.items()])
        await call.message.answer(
            f"✅ <b>Парсинг завершён!</b>\n\n{result_lines}\n\n"
            f"📊 Итого в базе: <b>{total:,}</b> записей",
            reply_markup=admin_menu_kb(), parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Parse task error: {e}")
        await call.message.answer(
            f"❌ <b>Ошибка парсинга:</b>\n<code>{str(e)}</code>\n\n"
            "Убедись что API_ID и API_HASH настроены в config.py",
            reply_markup=admin_menu_kb(), parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_clear_cache")
async def clear_cache(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔️ Только для главного администратора", show_alert=True)
        return
    db.clear_cache()
    await call.answer("✅ Кэш очищен!", show_alert=True)
    await back_to_admin(call)


@router.callback_query(F.data == "admin_logs")
async def admin_logs(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔️ Только для главного администратора", show_alert=True)
        return
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT cl.query, cl.result_found, cl.checked_at, u.username
        FROM check_log cl
        LEFT JOIN users u ON cl.user_id = u.telegram_id
        ORDER BY cl.checked_at DESC LIMIT 15
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await call.answer("Логов пока нет", show_alert=True)
        return

    lines = ["📋 <b>Последние 15 проверок:</b>\n"]
    for row in rows:
        emoji = "🚨" if row["result_found"] else "✅"
        user = f"@{row['username']}" if row["username"] else "аноним"
        date = str(row["checked_at"])[:16]
        lines.append(f"{emoji} <code>{row['query']}</code> — {user} [{date}]")

    await call.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb(), parse_mode="HTML")


# ==============================
# КАНАЛЫ (оба типа админов)
# ==============================

@router.callback_query(F.data == "admin_channels")
async def admin_channels(call: CallbackQuery):
    channels = db.get_channels()
    active = sum(1 for c in channels if c["is_active"])
    text = (
        f"📡 <b>Каналы-источники</b>\n\n"
        f"Всего: <b>{len(channels)}</b> · Активных: <b>{active}</b>\n\n"
        "✅ — активен | ❌ — отключён"
    ) if channels else "📡 <b>Каналы-источники</b>\n\nКаналов ещё нет. Добавь первый!"
    await call.message.edit_text(text, reply_markup=channels_list_kb(channels), parse_mode="HTML")


@router.callback_query(F.data.startswith("ch_view:"))
async def view_channel(call: CallbackQuery):
    channel_id = int(call.data.split(":")[1])
    ch = next((c for c in db.get_channels() if c["id"] == channel_id), None)
    if not ch:
        await call.answer("Канал не найден", show_alert=True)
        return
    status = "✅ Активен" if ch["is_active"] else "❌ Отключён"
    last = ch["last_parsed"][:16] if ch["last_parsed"] else "ещё не парсился"
    text = (
        f"📡 <b>@{ch['username']}</b>\n\n"
        f"Статус: {status}\n"
        f"Записей собрано: <b>{ch['records_count']:,}</b>\n"
        f"Последний парсинг: {last}\n"
        f"Добавлен: {str(ch['added_at'])[:10]}"
    )
    await call.message.edit_text(text, reply_markup=channel_detail_kb(channel_id, ch["is_active"]), parse_mode="HTML")


@router.callback_query(F.data.startswith("ch_toggle:"))
async def toggle_channel(call: CallbackQuery):
    channel_id = int(call.data.split(":")[1])
    new_status = db.toggle_channel(channel_id)
    await call.answer(f"Канал {'включён ✅' if new_status else 'отключён ❌'}", show_alert=True)
    await view_channel(call)


@router.callback_query(F.data.startswith("ch_delete:"))
async def delete_channel(call: CallbackQuery):
    channel_id = int(call.data.split(":")[1])
    db.delete_channel(channel_id)
    db.clear_cache()
    await call.answer("🗑 Канал удалён", show_alert=True)
    await admin_channels(call)


@router.callback_query(F.data == "ch_add")
async def ask_channel_username(call: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelStates.waiting_username)
    await call.message.edit_text(
        "📡 <b>Добавление канала</b>\n\n"
        "Введи username канала:\n"
        "<i>Например: @ScamChannel или ScamChannel</i>\n\n"
        "⚠️ Канал должен быть публичным",
        reply_markup=cancel_kb(), parse_mode="HTML"
    )


@router.message(ChannelStates.waiting_username)
async def process_channel_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@").lower()
    if len(username) < 3 or " " in username:
        await message.answer("❌ Неверный формат. Введи username без пробелов:", reply_markup=cancel_kb())
        return
    await state.clear()
    added = db.add_channel(username)
    uid = message.from_user.id
    menu = admin_menu_kb() if is_owner(uid) else subadmin_menu_kb()
    if not added:
        await message.answer(f"⚠️ Канал <b>@{username}</b> уже есть в списке.", reply_markup=menu, parse_mode="HTML")
        return
    await message.answer(
        f"✅ Канал <b>@{username}</b> добавлен!\n\nНажми «🔄 Обновить базу» чтобы спарсить его.",
        reply_markup=channels_list_kb(db.get_channels()), parse_mode="HTML"
    )


# ==============================
# СУБ-АДМИНЫ (только главный)
# ==============================

@router.callback_query(F.data == "admin_subadmins")
async def admin_subadmins(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔️ Только для главного администратора", show_alert=True)
        return
    subadmins = db.get_subadmins()
    text = (
        f"🔑 <b>Суб-администраторы ({len(subadmins)})</b>\n\n"
        "✅ Могут: добавлять мошенников и каналы\n"
        "⛔️ Не могут: управлять суб-админами, смотреть логи, запускать парсинг"
    ) if subadmins else (
        "🔑 <b>Суб-администраторы</b>\n\n"
        "Суб-админов ещё нет.\n\n"
        "Добавь пользователя по его Telegram ID.\n"
        "💡 ID можно узнать через @userinfobot"
    )
    await call.message.edit_text(text, reply_markup=subadmins_list_kb(subadmins), parse_mode="HTML")


@router.callback_query(F.data == "subadmin_add")
async def ask_subadmin_id(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    await state.set_state(SubadminStates.waiting_id)
    await call.message.edit_text(
        "🔑 <b>Добавление суб-админа</b>\n\n"
        "Введи <b>Telegram ID</b> пользователя:\n\n"
        "💡 Узнать ID: @userinfobot",
        reply_markup=cancel_kb(), parse_mode="HTML"
    )


@router.message(SubadminStates.waiting_id)
async def process_subadmin_id(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        await state.clear()
        return
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ ID должен быть числом. Попробуй снова:", reply_markup=cancel_kb())
        return
    new_id = int(text)
    await state.clear()
    if new_id in ADMIN_IDS:
        await message.answer("⚠️ Это уже главный администратор.", reply_markup=admin_menu_kb())
        return
    added = db.add_subadmin(telegram_id=new_id, username="", first_name="", added_by=message.from_user.id)
    if not added:
        await message.answer(
            f"⚠️ <code>{new_id}</code> уже является суб-админом.",
            reply_markup=admin_menu_kb(), parse_mode="HTML"
        )
        return
    await message.answer(
        f"✅ Суб-админ <code>{new_id}</code> добавлен!\n\n"
        "Теперь он может добавлять мошенников и каналы через /admin.",
        reply_markup=subadmins_list_kb(db.get_subadmins()), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("subadmin_del:"))
async def delete_subadmin(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔️ Нет доступа", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    db.remove_subadmin(uid)
    await call.answer("🗑 Суб-админ удалён", show_alert=True)
    subadmins = db.get_subadmins()
    text = f"🔑 <b>Суб-администраторы ({len(subadmins)})</b>" if subadmins else "🔑 <b>Суб-администраторы</b>\n\nСуб-админов нет."
    await call.message.edit_text(text, reply_markup=subadmins_list_kb(subadmins), parse_mode="HTML")
