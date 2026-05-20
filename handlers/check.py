import re
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import cancel_kb, check_result_kb, main_menu_kb

router = Router()
logger = logging.getLogger(__name__)

RE_DIGITS = re.compile(r'^\d{5,12}$')
CONTACT = "@nemurovv"


class CheckStates(StatesGroup):
    waiting_id = State()
    waiting_username = State()


# ==============================
# КНОПКИ — выбор типа проверки
# ==============================

@router.callback_query(F.data == "check_by_id")
async def ask_for_id(call: CallbackQuery, state: FSMContext):
    await state.set_state(CheckStates.waiting_id)
    await call.message.edit_text(
        "🔍 <b>Проверка по Telegram ID</b>\n\n"
        "Введи числовой ID пользователя:\n"
        "<i>Например: 123456789</i>\n\n"
        "💡 Узнать ID можно через @userinfobot",
        reply_markup=cancel_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "check_by_username")
async def ask_for_username(call: CallbackQuery, state: FSMContext):
    await state.set_state(CheckStates.waiting_username)
    await call.message.edit_text(
        "🔎 <b>Проверка по @username</b>\n\n"
        "Введи username пользователя:\n"
        "<i>Например: @username или username</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.start import get_welcome_text
    await call.message.edit_text(get_welcome_text(), reply_markup=main_menu_kb(), parse_mode="HTML")


# ==============================
# ОБРАБОТКА ВВОДА
# ==============================

@router.message(CheckStates.waiting_id)
async def process_id_check(message: Message, state: FSMContext):
    query = message.text.strip()
    if not RE_DIGITS.match(query):
        await message.answer("❌ Неверный формат. Введи числовой ID (5–12 цифр):", reply_markup=cancel_kb())
        return
    await state.clear()
    await _do_check(message, query, by="id")


@router.message(CheckStates.waiting_username)
async def process_username_check(message: Message, state: FSMContext):
    query = message.text.strip().lstrip("@")
    if len(query) < 3 or not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,31}$', query):
        await message.answer("❌ Неверный username. Попробуй снова:", reply_markup=cancel_kb())
        return
    await state.clear()
    await _do_check(message, query, by="username")


@router.message(F.text.regexp(r'^/check_?\d+$'))
async def check_by_command(message: Message):
    match = re.search(r'\d+', message.text)
    if match:
        await _do_check(message, match.group(), by="id")


@router.message(F.text.regexp(r'^\d{5,12}$'))
async def auto_check_id(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        return
    await _do_check(message, message.text.strip(), by="id")


@router.message(F.text.regexp(r'^@[a-zA-Z][a-zA-Z0-9_]{3,31}$'))
async def auto_check_username(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        return
    await _do_check(message, message.text.strip().lstrip("@"), by="username")


# ==============================
# ЯДРО ПОИСКА
# ==============================

async def _do_check(message: Message, query: str, by: str):
    from config import ADMIN_IDS
    uid = message.from_user.id
    query_clean = query.strip()

    # Пропускаем ограничения для админов/суб-админов
    is_privileged = uid in ADMIN_IDS or db.is_subadmin(uid)
    is_sub = db.has_active_subscription(uid)
    is_free = not is_privileged and not is_sub

    # --- Кулдаун для бесплатных ---
    if is_free:
        remaining = db.check_cooldown(uid)
        if remaining > 0:
            await message.answer(
                f"⏳ <b>Подождите {remaining} сек.</b>\n\n"
                f"Бесплатным пользователям доступна одна проверка раз в {db.COOLDOWN_SECONDS} секунд.\n\n"
                f"💎 Купите подписку у {CONTACT} для мгновенных проверок.",
                reply_markup=check_result_kb(query_clean, False),
                parse_mode="HTML"
            )
            return
        db.update_cooldown(uid)

    loading_msg = await message.answer("🔍 <b>Проверяю...</b>", parse_mode="HTML")

    # --- Поиск ---
    cache_key = f"{by}:{query_clean.lower()}"
    cached = db.get_cached(cache_key)

    if cached:
        db_results = cached.get("db_results", [])
        live_results = cached.get("live_results", [])
        manual_results = cached.get("manual_results", [])
    else:
        if by == "id":
            db_results = db.search_scammer_by_id(query_clean)
            manual_results = db.search_manual_by_id(query_clean)
        else:
            db_results = db.search_scammer_by_username(query_clean)
            manual_results = db.search_manual_by_username(query_clean)

        live_results = []
        try:
            from parser import search_in_channels_live
            live_results = await search_in_channels_live(query_clean)
        except Exception as e:
            logger.warning(f"Live search failed: {e}")

        db.set_cache(cache_key, {
            "db_results": db_results,
            "live_results": live_results,
            "manual_results": manual_results,
        })

    found = bool(db_results or live_results or manual_results)
    db.log_check(uid, query_clean, found)
    db.increment_user_checks(uid)

    await loading_msg.delete()

    # --- Медиадоказательства (только для подписчиков/админов) ---
    if found and manual_results and not is_free:
        for rec in manual_results[:3]:
            for entry in rec.get("media_file_ids", [])[:5]:
                try:
                    kind, file_id = entry.split(":", 1)
                    caption = "📎 Доказательство"
                    if kind == "photo":
                        await message.answer_photo(file_id, caption=caption)
                    elif kind == "video":
                        await message.answer_video(file_id, caption=caption)
                    elif kind == "document":
                        await message.answer_document(file_id, caption=caption)
                except Exception:
                    pass

    text = _format_result(query_clean, by, db_results, live_results, manual_results, is_free=is_free)

    await message.answer(
        text,
        reply_markup=check_result_kb(query_clean, found),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# ==============================
# ФОРМАТИРОВАНИЕ
# ==============================

def _format_result(query: str, by: str,
                   db_results: list, live_results: list,
                   manual_results: list = None, is_free: bool = False) -> str:
    if manual_results is None:
        manual_results = []
    label = f"ID <code>{query}</code>" if by == "id" else f"@{query}"

    # --- Чист ---
    if not db_results and not live_results and not manual_results:
        text = (
            f"✅ <b>Проверка: {label}</b>\n\n"
            "🟢 <b>Совпадений не найдено</b>\n\n"
            "Пользователь не обнаружен в базах мошенников.\n\n"
            "⚠️ <i>Это не гарантия честности — база обновляется периодически.</i>"
        )
        if is_free:
            text += f"\n\n💎 <b>Купите подписку у {CONTACT}</b> для полного доступа к базе."
        return text

    # --- Найден ---
    total = len(db_results) + len(live_results) + len(manual_results)
    lines = [
        f"🚨 <b>Проверка: {label}</b>\n",
        f"🔴 <b>НАЙДЕНО {total} упоминаний в базе мошенников!</b>",
    ]

    if is_free:
        # Бесплатный — только итог, без деталей
        lines.append(
            "\n🔒 <b>Подробности скрыты</b>\n\n"
            "Для просмотра полной информации,\n"
            "доказательств и деталей:\n\n"
            f"💎 <b>Купите подписку у {CONTACT}</b>\n"
            f"   • Неделя — 1$ | Месяц — 4$"
        )
    else:
        # Полный доступ
        if manual_results:
            lines.append(f"\n⛔️ <b>Подтверждённые случаи ({len(manual_results)}):</b>")
            for r in manual_results:
                parts = []
                if r.get("telegram_id"):
                    parts.append(f"ID: <code>{r['telegram_id']}</code>")
                if r.get("username"):
                    parts.append(f"@{r['username']}")
                if r.get("full_name"):
                    parts.append(r["full_name"])
                if parts:
                    lines.append(f"\n👤 {' | '.join(parts)}")
                desc = r.get("description", "")[:300]
                if desc:
                    lines.append(f"📝 {_escape(desc)}")
                media_count = len(r.get("media_file_ids", []))
                if media_count:
                    lines.append(f"📎 Доказательств: {media_count} файл(ов) ⬆️")
                date = str(r.get("added_at", ""))[:10]
                if date:
                    lines.append(f"📅 {date}")

        if db_results:
            lines.append(f"\n📂 <b>Из мониторинга ({len(db_results)} записей):</b>")
            for rec in db_results[:3]:
                msg_text = rec.get("message_text", "")[:200].strip()
                date = str(rec.get("message_date", ""))[:10]
                if msg_text:
                    lines.append(f"\n💬 <i>{_escape(msg_text)}...</i>")
                if date:
                    lines.append(f"   📅 {date}")

        if live_results:
            lines.append(f"\n🔴 <b>Свежие данные ({len(live_results)}):</b>")
            for r in live_results[:3]:
                text_preview = r.get("text", "")[:200].strip()
                date = r.get("date", "")
                if text_preview:
                    lines.append(f"\n💬 <i>{_escape(text_preview)}...</i>")
                if date:
                    lines.append(f"   📅 {date}")

    lines.append("\n⛔️ <b>Рекомендуем не проводить сделки с данным пользователем.</b>")
    return "\n".join(lines)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
