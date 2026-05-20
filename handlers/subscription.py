import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import main_menu_kb, back_to_main_kb, cancel_kb, subscription_kb

router = Router()
logger = logging.getLogger(__name__)

CONTACT = "@nemurovv"
PRICES = {"week": "1$", "month": "4$"}


class SubStates(StatesGroup):
    waiting_key = State()


def _sub_promo_text() -> str:
    return (
        f"\n\n💎 <b>Купите подписку у {CONTACT}</b>\n"
        f"   • Неделя — {PRICES['week']} | Месяц — {PRICES['month']}"
    )


# ==============================
# РАЗДЕЛ ПОДПИСКИ
# ==============================

@router.callback_query(F.data == "subscription")
async def show_subscription(call: CallbackQuery):
    uid = call.from_user.id
    sub = db.get_subscription(uid)

    if sub and sub["is_active"]:
        expires = str(sub["expires_at"])[:16].replace("T", " ")
        plan_label = db.PLAN_LABELS.get(sub["plan"], sub["plan"])
        text = (
            "💎 <b>Ваша подписка</b>\n\n"
            f"✅ <b>Активна</b>\n"
            f"📋 Тариф: {plan_label}\n"
            f"📅 Действует до: <b>{expires}</b>\n\n"
            "Полный доступ к результатам проверок без ограничений и задержек."
        )
    else:
        text = (
            "💎 <b>Подписка OpusGuru</b>\n\n"
            "❌ У вас нет активной подписки\n\n"
            "<b>Что даёт подписка:</b>\n"
            "✅ Полные результаты проверок\n"
            "✅ Все доказательства и детали\n"
            "✅ Без задержки между проверками\n"
            "✅ Приоритетный поиск\n\n"
            "<b>Тарифы:</b>\n"
            f"   • 📅 Неделя — <b>{PRICES['week']}</b>\n"
            f"   • 🗓 Месяц — <b>{PRICES['month']}</b>\n\n"
            f"Для покупки обратитесь к {CONTACT}\n"
            "После оплаты вы получите ключ активации."
        )
    await call.message.edit_text(text, reply_markup=subscription_kb(bool(sub and sub["is_active"])),
                                 parse_mode="HTML")


@router.callback_query(F.data == "sub_activate")
async def ask_key(call: CallbackQuery, state: FSMContext):
    await state.set_state(SubStates.waiting_key)
    await call.message.edit_text(
        "🔑 <b>Активация ключа</b>\n\n"
        "Введи ключ подписки который тебе прислали:\n"
        "<i>Формат: OG-XXXXXXXXXXXX</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML"
    )


@router.message(SubStates.waiting_key)
async def process_key(message: Message, state: FSMContext):
    await state.clear()
    key = message.text.strip().upper()
    uid = message.from_user.id

    result = db.activate_key(key, uid)

    if not result["ok"]:
        reason = result["reason"]
        if reason == "not_found":
            text = (
                "❌ <b>Ключ не найден</b>\n\n"
                "Проверь правильность ввода.\n"
                f"Если проблема не решается — обратись к {CONTACT}"
            )
        elif reason == "already_used":
            text = (
                "❌ <b>Ключ уже использован</b>\n\n"
                f"Этот ключ был активирован ранее.\n"
                f"Обратись к {CONTACT} за новым ключом."
            )
        else:
            text = f"❌ Ошибка активации. Обратись к {CONTACT}"
        await message.answer(text, reply_markup=back_to_main_kb(), parse_mode="HTML")
        return

    expires = str(result["expires_at"])[:16].replace("T", " ")
    plan_label = db.PLAN_LABELS.get(result["plan"], result["plan"])

    await message.answer(
        f"🎉 <b>Подписка активирована!</b>\n\n"
        f"📋 Тариф: {plan_label}\n"
        f"📅 Действует до: <b>{expires}</b>\n\n"
        "Теперь вам доступны полные результаты проверок без ограничений!",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
