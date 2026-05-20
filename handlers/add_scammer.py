import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import BaseFilter

import database as db
from config import ADMIN_IDS
from keyboards import admin_menu_kb, skip_kb, done_media_kb, cancel_kb, manual_record_kb

router = Router()
logger = logging.getLogger(__name__)


class IsAnyAdmin(BaseFilter):
    """Главный админ ИЛИ суб-админ."""
    async def __call__(self, event) -> bool:
        uid = getattr(getattr(event, "from_user", None), "id", None)
        if uid in ADMIN_IDS:
            return True
        return db.is_subadmin(uid)


router.message.filter(IsAnyAdmin())
router.callback_query.filter(IsAnyAdmin())


class AddScammerStates(StatesGroup):
    waiting_id = State()
    waiting_username = State()
    waiting_fullname = State()
    waiting_description = State()
    waiting_media = State()


# ==============================
# НАЧАЛО ДОБАВЛЕНИЯ
# ==============================

@router.callback_query(F.data == "admin_add_scammer")
async def start_add_scammer(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddScammerStates.waiting_id)
    await state.update_data(media_file_ids=[])
    await call.message.edit_text(
        "➕ <b>Добавление мошенника</b>\n\n"
        "Шаг 1️⃣ — Введи <b>Telegram ID</b> мошенника\n"
        "<i>Только цифры, например: 123456789</i>\n\n"
        "Не знаешь ID? Нажми «Пропустить»",
        reply_markup=skip_kb("skip_scammer_id"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "skip_scammer_id")
async def skip_id(call: CallbackQuery, state: FSMContext):
    await state.update_data(telegram_id="")
    await state.set_state(AddScammerStates.waiting_username)
    await call.message.edit_text(
        "Шаг 2️⃣ — Введи <b>@username</b> мошенника\n"
        "<i>Например: @username или username</i>",
        reply_markup=skip_kb("skip_scammer_username"),
        parse_mode="HTML"
    )


@router.message(AddScammerStates.waiting_id)
async def process_scammer_id(message: Message, state: FSMContext):
    tid = message.text.strip()
    if not tid.isdigit():
        await message.answer(
            "❌ ID должен содержать только цифры. Попробуй снова:",
            reply_markup=skip_kb("skip_scammer_id")
        )
        return
    await state.update_data(telegram_id=tid)
    await state.set_state(AddScammerStates.waiting_username)
    await message.answer(
        "Шаг 2️⃣ — Введи <b>@username</b> мошенника\n"
        "<i>Например: @username или username</i>",
        reply_markup=skip_kb("skip_scammer_username"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "skip_scammer_username")
async def skip_username(call: CallbackQuery, state: FSMContext):
    await state.update_data(username="")
    await state.set_state(AddScammerStates.waiting_fullname)
    await call.message.edit_text(
        "Шаг 3️⃣ — Введи <b>имя/никнейм</b> мошенника\n"
        "<i>Как он себя называет, имя в профиле</i>",
        reply_markup=skip_kb("skip_scammer_fullname"),
        parse_mode="HTML"
    )


@router.message(AddScammerStates.waiting_username)
async def process_scammer_username(message: Message, state: FSMContext):
    uname = message.text.strip().lstrip("@").lower()
    await state.update_data(username=uname)
    await state.set_state(AddScammerStates.waiting_fullname)
    await message.answer(
        "Шаг 3️⃣ — Введи <b>имя/никнейм</b> мошенника\n"
        "<i>Как он себя называет, имя в профиле</i>",
        reply_markup=skip_kb("skip_scammer_fullname"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "skip_scammer_fullname")
async def skip_fullname(call: CallbackQuery, state: FSMContext):
    await state.update_data(full_name="")
    await state.set_state(AddScammerStates.waiting_description)
    await call.message.edit_text(
        "Шаг 4️⃣ — Опиши <b>схему мошенничества</b>\n\n"
        "Что произошло? Какая сумма? Как обманул?\n"
        "<i>Минимум 10 символов</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML"
    )


@router.message(AddScammerStates.waiting_fullname)
async def process_scammer_fullname(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(AddScammerStates.waiting_description)
    await message.answer(
        "Шаг 4️⃣ — Опиши <b>схему мошенничества</b>\n\n"
        "Что произошло? Какая сумма? Как обманул?\n"
        "<i>Минимум 10 символов</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML"
    )


@router.message(AddScammerStates.waiting_description)
async def process_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if len(desc) < 10:
        await message.answer(
            "❌ Описание слишком короткое. Минимум 10 символов:",
            reply_markup=cancel_kb()
        )
        return
    await state.update_data(description=desc)
    await state.set_state(AddScammerStates.waiting_media)
    await message.answer(
        "Шаг 5️⃣ — Прикрепи <b>доказательства</b>\n\n"
        "Отправь фото, видео или документы по одному.\n"
        "Когда всё загрузишь — нажми «Готово».\n\n"
        "Можно отправить несколько файлов подряд.",
        reply_markup=done_media_kb(),
        parse_mode="HTML"
    )


# ==============================
# ПРИЁМ МЕДИА
# ==============================

@router.message(AddScammerStates.waiting_media, F.photo)
async def receive_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await _append_media(state, f"photo:{file_id}")
    data = await state.get_data()
    count = len(data.get("media_file_ids", []))
    await message.answer(
        f"✅ Фото добавлено ({count} файл(ов) всего)\n"
        "Отправь ещё или нажми «Готово»",
        reply_markup=done_media_kb()
    )


@router.message(AddScammerStates.waiting_media, F.video)
async def receive_video(message: Message, state: FSMContext):
    file_id = message.video.file_id
    await _append_media(state, f"video:{file_id}")
    data = await state.get_data()
    count = len(data.get("media_file_ids", []))
    await message.answer(
        f"✅ Видео добавлено ({count} файл(ов) всего)\n"
        "Отправь ещё или нажми «Готово»",
        reply_markup=done_media_kb()
    )


@router.message(AddScammerStates.waiting_media, F.document)
async def receive_document(message: Message, state: FSMContext):
    file_id = message.document.file_id
    await _append_media(state, f"document:{file_id}")
    data = await state.get_data()
    count = len(data.get("media_file_ids", []))
    await message.answer(
        f"✅ Документ добавлен ({count} файл(ов) всего)\n"
        "Отправь ещё или нажми «Готово»",
        reply_markup=done_media_kb()
    )


async def _append_media(state: FSMContext, file_entry: str):
    data = await state.get_data()
    media = data.get("media_file_ids", [])
    media.append(file_entry)
    await state.update_data(media_file_ids=media)


# ==============================
# СОХРАНЕНИЕ
# ==============================

@router.callback_query(AddScammerStates.waiting_media, F.data == "add_scammer_done")
async def save_scammer(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    tid = data.get("telegram_id", "")
    username = data.get("username", "")
    full_name = data.get("full_name", "")
    description = data.get("description", "")
    media = data.get("media_file_ids", [])

    if not tid and not username and not full_name:
        await call.message.edit_text(
            "❌ Нужно указать хотя бы ID, username или имя мошенника.",
            reply_markup=admin_menu_kb()
        )
        return

    record_id = db.add_manual_scammer(
        telegram_id=tid,
        username=username,
        full_name=full_name,
        description=description,
        media_file_ids=media,
        added_by=call.from_user.id
    )

    # Очищаем кэш — запись новая
    db.clear_cache()

    parts = []
    if tid:
        parts.append(f"ID: <code>{tid}</code>")
    if username:
        parts.append(f"@{username}")
    if full_name:
        parts.append(full_name)

    await call.message.edit_text(
        f"✅ <b>Мошенник добавлен в базу!</b>\n\n"
        f"👤 {' | '.join(parts)}\n"
        f"📎 Доказательств: {len(media)} файл(ов)\n"
        f"🆔 Запись #{record_id}",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


# ==============================
# ПРОСМОТР И УДАЛЕНИЕ
# ==============================

@router.callback_query(F.data == "admin_list_manual")
async def list_manual(call: CallbackQuery):
    records = db.get_all_manual_scammers(limit=10)
    if not records:
        await call.message.edit_text(
            "📂 Ручных записей пока нет.\n\nДобавь мошенника через «➕ Добавить мошенника»",
            reply_markup=admin_menu_kb()
        )
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()

    lines = [f"📂 <b>Ручные записи ({len(records)}):</b>\n"]
    for r in records:
        parts = []
        if r["telegram_id"]:
            parts.append(f"ID {r['telegram_id']}")
        if r["username"]:
            parts.append(f"@{r['username']}")
        if r["full_name"]:
            parts.append(r["full_name"])
        label = " | ".join(parts) if parts else f"Запись #{r['id']}"
        date = str(r["added_at"])[:10]
        media_count = len(r["media_file_ids"])
        lines.append(f"#{r['id']} — {label} [{date}] 📎{media_count}")
        builder.row(InlineKeyboardButton(
            text=f"#{r['id']} {label[:30]}",
            callback_data=f"admin_view_manual:{r['id']}"
        ))

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu"))
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_view_manual:"))
async def view_manual_record(call: CallbackQuery):
    record_id = int(call.data.split(":")[1])
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM manual_scammers WHERE id = ?", (record_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        await call.answer("Запись не найдена", show_alert=True)
        return

    import json
    r = dict(row)
    media = json.loads(r.get("media_file_ids") or "[]")

    parts = []
    if r["telegram_id"]:
        parts.append(f"🆔 ID: <code>{r['telegram_id']}</code>")
    if r["username"]:
        parts.append(f"👤 @{r['username']}")
    if r["full_name"]:
        parts.append(f"📛 {r['full_name']}")

    text = (
        f"📋 <b>Запись #{r['id']}</b>\n\n"
        + "\n".join(parts) +
        f"\n\n📝 {r['description']}\n\n"
        f"📎 Доказательств: {len(media)} файл(ов)\n"
        f"📅 Добавлено: {str(r['added_at'])[:16]}"
    )

    await call.message.edit_text(
        text,
        reply_markup=manual_record_kb(record_id),
        parse_mode="HTML"
    )

    # Отправляем медиафайлы отдельными сообщениями
    if media:
        for entry in media[:10]:
            try:
                kind, file_id = entry.split(":", 1)
                if kind == "photo":
                    await call.message.answer_photo(file_id, caption="📸 Доказательство")
                elif kind == "video":
                    await call.message.answer_video(file_id, caption="🎥 Доказательство")
                elif kind == "document":
                    await call.message.answer_document(file_id, caption="📄 Доказательство")
            except Exception as e:
                logger.warning(f"Media send error: {e}")


@router.callback_query(F.data.startswith("admin_del_manual:"))
async def delete_manual_record(call: CallbackQuery):
    record_id = int(call.data.split(":")[1])
    db.delete_manual_scammer(record_id)
    db.clear_cache()
    await call.answer("🗑 Запись удалена", show_alert=True)
    await list_manual(call)
