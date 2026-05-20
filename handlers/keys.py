import logging
from aiogram import Router, F
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS
from keyboards import (
    admin_menu_kb, cancel_kb,
    keys_menu_kb, key_plans_kb, key_custom_days_kb, keys_list_kb
)

router = Router()
logger = logging.getLogger(__name__)


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        uid = getattr(getattr(event, "from_user", None), "id", None)
        return uid in ADMIN_IDS


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class KeyStates(StatesGroup):
    waiting_custom_days = State()
    waiting_grant_id = State()
    waiting_grant_days = State()
    waiting_revoke_id = State()


# ==============================
# МЕНЮ КЛЮЧЕЙ
# ==============================

@router.callback_query(F.data == "admin_keys")
async def keys_menu(call: CallbackQuery):
    keys = db.get_keys(show_used=False)
    text = (
        "🔑 <b>Управление ключами подписки</b>\n\n"
        f"Активных ключей: <b>{len(keys)}</b>\n\n"
        "Выбери действие:"
    )
    await call.message.edit_text(text, reply_markup=keys_menu_kb(), parse_mode="HTML")


# ==============================
# СОЗДАНИЕ КЛЮЧА
# ==============================

@router.callback_query(F.data == "key_create")
async def choose_plan(call: CallbackQuery):
    await call.message.edit_text(
        "🔑 <b>Создание ключа</b>\n\n"
        "Выбери тариф:",
        reply_markup=key_plans_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("key_plan:"))
async def create_key_by_plan(call: CallbackQuery, state: FSMContext):
    plan = call.data.split(":")[1]

    if plan == "custom":
        await state.set_state(KeyStates.waiting_custom_days)
        await call.message.edit_text(
            "🔑 <b>Кастомный срок</b>\n\n"
            "Введи количество дней подписки:",
            reply_markup=cancel_kb(),
            parse_mode="HTML"
        )
        return

    days = db.PLAN_DAYS.get(plan, 30)
    key = db.create_key(plan=plan, days=days, created_by=call.from_user.id)
    plan_label = db.PLAN_LABELS.get(plan, plan)

    await call.message.edit_text(
        f"✅ <b>Ключ создан!</b>\n\n"
        f"🔑 <code>{key}</code>\n\n"
        f"📋 Тариф: {plan_label} ({days} дней)\n\n"
        "Скопируй и отправь пользователю.\n"
        "<i>Ключ одноразовый и сгорит после активации.</i>",
        reply_markup=keys_menu_kb(),
        parse_mode="HTML"
    )


@router.message(KeyStates.waiting_custom_days)
async def create_custom_key(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 3650):
        await message.answer(
            "❌ Введи число от 1 до 3650:",
            reply_markup=cancel_kb()
        )
        return
    days = int(text)
    await state.clear()
    key = db.create_key(plan="custom", days=days, created_by=message.from_user.id)
    await message.answer(
        f"✅ <b>Ключ создан!</b>\n\n"
        f"🔑 <code>{key}</code>\n\n"
        f"📋 Кастомный срок: {days} дней\n\n"
        "Скопируй и отправь пользователю.\n"
        "<i>Ключ одноразовый.</i>",
        reply_markup=keys_menu_kb(),
        parse_mode="HTML"
    )


# ==============================
# СПИСОК КЛЮЧЕЙ
# ==============================

@router.callback_query(F.data == "keys_list")
async def list_keys(call: CallbackQuery):
    keys = db.get_keys(show_used=False)
    if not keys:
        await call.message.edit_text(
            "📋 <b>Активные ключи</b>\n\nАктивных ключей нет.",
            reply_markup=keys_menu_kb(),
            parse_mode="HTML"
        )
        return
    await call.message.edit_text(
        f"📋 <b>Активные ключи ({len(keys)})</b>\n\n"
        "Нажми на ключ чтобы удалить:",
        reply_markup=keys_list_kb(keys),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "keys_list_used")
async def list_used_keys(call: CallbackQuery):
    keys = db.get_keys(show_used=True)
    used = [k for k in keys if k["is_used"]]
    if not used:
        await call.answer("Использованных ключей нет", show_alert=True)
        return
    lines = [f"📋 <b>Использованные ключи ({len(used)}):</b>\n"]
    for k in used[:15]:
        plan = db.PLAN_LABELS.get(k["plan"], k["plan"])
        used_at = str(k["used_at"] or "")[:10]
        lines.append(f"<code>{k['key']}</code> — {plan} · использован {used_at}")
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=keys_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("key_delete:"))
async def delete_key(call: CallbackQuery):
    key = call.data.split(":", 1)[1]
    db.delete_key(key)
    await call.answer("🗑 Ключ удалён", show_alert=True)
    await list_keys(call)


# ==============================
# РУЧНАЯ ВЫДАЧА / ОТЗЫВ ПОДПИСКИ
# ==============================

@router.callback_query(F.data == "key_grant_manual")
async def ask_grant_id(call: CallbackQuery, state: FSMContext):
    await state.set_state(KeyStates.waiting_grant_id)
    await call.message.edit_text(
        "👤 <b>Ручная выдача подписки</b>\n\n"
        "Введи Telegram ID пользователя:",
        reply_markup=cancel_kb(),
        parse_mode="HTML"
    )


@router.message(KeyStates.waiting_grant_id)
async def ask_grant_days(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Введи числовой ID:", reply_markup=cancel_kb())
        return
    await state.update_data(grant_id=int(message.text.strip()))
    await state.set_state(KeyStates.waiting_grant_days)
    await message.answer(
        "📅 Сколько дней выдать подписку?\n<i>Введи число:</i>",
        reply_markup=key_custom_days_kb(),
        parse_mode="HTML"
    )


@router.callback_query(KeyStates.waiting_grant_days, F.data.startswith("grant_days:"))
async def grant_quick_days(call: CallbackQuery, state: FSMContext):
    days = int(call.data.split(":")[1])
    data = await state.get_data()
    await state.clear()
    uid = data["grant_id"]
    expires = db.grant_subscription(uid, days, "manual", key="manual_grant")
    expires_fmt = str(expires)[:16].replace("T", " ")
    await call.message.edit_text(
        f"✅ Подписка выдана пользователю <code>{uid}</code>\n"
        f"📅 До: <b>{expires_fmt}</b> ({days} дней)",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


@router.message(KeyStates.waiting_grant_days)
async def grant_custom_days(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Введи число дней:", reply_markup=cancel_kb())
        return
    days = int(message.text.strip())
    data = await state.get_data()
    await state.clear()
    uid = data["grant_id"]
    expires = db.grant_subscription(uid, days, "manual", key="manual_grant")
    expires_fmt = str(expires)[:16].replace("T", " ")
    await message.answer(
        f"✅ Подписка выдана пользователю <code>{uid}</code>\n"
        f"📅 До: <b>{expires_fmt}</b> ({days} дней)",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "key_revoke")
async def ask_revoke_id(call: CallbackQuery, state: FSMContext):
    await state.set_state(KeyStates.waiting_revoke_id)
    await call.message.edit_text(
        "🚫 <b>Отозвать подписку</b>\n\n"
        "Введи Telegram ID пользователя:",
        reply_markup=cancel_kb(),
        parse_mode="HTML"
    )


@router.message(KeyStates.waiting_revoke_id)
async def revoke_subscription(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Введи числовой ID:", reply_markup=cancel_kb())
        return
    await state.clear()
    uid = int(message.text.strip())
    sub = db.get_subscription(uid)
    if not sub:
        await message.answer(
            f"⚠️ У пользователя <code>{uid}</code> нет подписки.",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML"
        )
        return
    db.revoke_subscription(uid)
    await message.answer(
        f"✅ Подписка пользователя <code>{uid}</code> отозвана.",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


# ==============================
# СПИСОК АКТИВНЫХ ПОДПИСЧИКОВ
# ==============================

@router.callback_query(F.data == "subs_list")
async def subs_list(call: CallbackQuery):
    subs = db.get_active_subscriptions()
    if not subs:
        await call.message.edit_text(
            "👥 <b>Активные подписчики</b>\n\nПодписчиков пока нет.",
            reply_markup=keys_menu_kb(),
            parse_mode="HTML"
        )
        return

    from keyboards import subs_list_kb
    text = f"👥 <b>Активные подписчики ({len(subs)})</b>\n\nНажми на пользователя чтобы управлять:"
    await call.message.edit_text(text, reply_markup=subs_list_kb(subs), parse_mode="HTML")


@router.callback_query(F.data.startswith("sub_view:"))
async def sub_view(call: CallbackQuery):
    uid = int(call.data.split(":")[1])
    sub = db.get_subscription(uid)
    if not sub:
        await call.answer("Подписка не найдена или истекла", show_alert=True)
        return

    username = sub.get("username") or ""
    first_name = sub.get("first_name") or ""
    plan_label = db.PLAN_LABELS.get(sub["plan"], sub["plan"])
    expires = str(sub["expires_at"])[:16].replace("T", " ")
    activated = str(sub["activated_at"])[:16].replace("T", " ")
    key = sub.get("activated_key") or "—"

    user_label = ""
    if first_name:
        user_label += first_name
    if username:
        user_label += f" (@{username})"
    if not user_label:
        user_label = f"ID {uid}"

    text = (
        f"👤 <b>{user_label}</b>\n"
        f"🆔 <code>{uid}</code>\n\n"
        f"📋 Тариф: {plan_label}\n"
        f"📅 Истекает: <b>{expires}</b>\n"
        f"🕐 Активировано: {activated}\n"
        f"🔑 Ключ: <code>{key}</code>"
    )

    from keyboards import sub_detail_kb
    await call.message.edit_text(text, reply_markup=sub_detail_kb(uid), parse_mode="HTML")


@router.callback_query(F.data.startswith("sub_revoke:"))
async def sub_revoke_inline(call: CallbackQuery):
    uid = int(call.data.split(":")[1])
    db.revoke_subscription(uid)
    await call.answer("✅ Подписка отозвана", show_alert=True)
    # Возвращаемся к списку
    await subs_list(call)
