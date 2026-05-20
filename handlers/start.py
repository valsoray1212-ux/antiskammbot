from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import main_menu_kb, back_to_main_kb

router = Router()


def get_welcome_text() -> str:
    return (
        "🛡 <b>OpusGuru Anti-Scam</b>\n\n"
        "Проверяю пользователей Telegram по базам мошенников.\n\n"
        "👇 Выбери действие:"
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    db.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or ""
    )
    has_sub = db.has_active_subscription(message.from_user.id)
    await message.answer(get_welcome_text(), reply_markup=main_menu_kb(has_sub), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def back_to_menu(call: CallbackQuery):
    has_sub = db.has_active_subscription(call.from_user.id)
    await call.message.edit_text(get_welcome_text(), reply_markup=main_menu_kb(has_sub), parse_mode="HTML")


@router.callback_query(F.data == "about")
async def about(call: CallbackQuery):
    text = (
        "🛡 <b>OpusGuru Anti-Scam</b>\n\n"
        "Бот проверяет пользователей Telegram по базам скам-репортов.\n\n"
        "<b>Как работает:</b>\n"
        "1️⃣ Вводишь Telegram ID или @username\n"
        "2️⃣ Бот проверяет по базе мошенников\n"
        "3️⃣ Показывает найденные репорты\n\n"
        "⚠️ <i>База обновляется периодически. "
        "Отсутствие в базе не гарантирует честность пользователя.</i>"
    )
    await call.message.edit_text(text, reply_markup=back_to_main_kb(),
                                 parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data == "new_check")
async def new_check(call: CallbackQuery):
    has_sub = db.has_active_subscription(call.from_user.id)
    await call.message.edit_text(get_welcome_text(), reply_markup=main_menu_kb(has_sub), parse_mode="HTML")
