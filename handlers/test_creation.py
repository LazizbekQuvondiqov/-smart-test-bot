# handlers/test_creation.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import re

import database as db
# --- XATO TUZATILDI: `main_menu_keyboard` import qilindi ---
from keyboards import test_duration_keyboard, main_menu_keyboard

router = Router()

class TestCreationStates(StatesGroup):
    waiting_for_file = State()
    waiting_for_answers = State()
    waiting_for_duration = State()

@router.message(F.text == "✍️ Yangi Test Yaratish")
async def start_test_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Yaxshi, yangi test yaratishni boshladik.\n\n"
        "<b>1-qadam:</b> Test savollari joylashgan faylni yuboring (PDF, DOCX, JPG, PNG).",
        reply_markup=None
    )
    await state.set_state(TestCreationStates.waiting_for_file)

@router.message(TestCreationStates.waiting_for_file, F.document | F.photo)
async def process_file(message: Message, state: FSMContext):
    file_id = None
    file_type = None
    if message.document:
        file_id = message.document.file_id
        file_type = 'document'
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'

    if not file_id:
        await message.reply("Iltimos, qo'llab-quvvatlanadigan turdagi fayl yuboring (rasm yoki dokument).")
        return

    await state.update_data(file_id=file_id, file_type=file_type)
    await message.answer(
        "✅ Fayl qabul qilindi.\n\n"
        "<b>2-qadam:</b> Endi test javoblarining kalitini yuboring. Javoblar faqat harflardan iborat bo'lishi kerak.\n\n"
        "Masalan: <code>1a2b3c4d...</code> yoki shunchaki <code>abcd...</code>"
    )
    await state.set_state(TestCreationStates.waiting_for_answers)

@router.message(TestCreationStates.waiting_for_answers, F.text)
async def process_answers(message: Message, state: FSMContext):
    clean_answers = re.sub(r'[^a-zA-Z]', '', message.text).lower()

    if not clean_answers:
        await message.answer(
            "❌ Javoblar kaliti formati noto'g'ri. Iltimos, faqat harflardan iborat kalit yuboring "
            "(masalan, <code>abcd...</code>)."
        )
        return

    await state.update_data(answers=clean_answers)
    num_questions = len(clean_answers)

    await message.answer(
        f"✅ Javoblar qabul qilindi. Sizning testingizda <b>{num_questions} ta</b> savol borligi aniqlandi.\n\n"
        "<b>3-qadam:</b> Endi har bir o'quvchiga testni yechish uchun qancha vaqt berilishini tanlang.",
        reply_markup=test_duration_keyboard()
    )
    await state.set_state(TestCreationStates.waiting_for_duration)

@router.callback_query(TestCreationStates.waiting_for_duration, F.data.startswith('duration_'))
async def process_duration(callback: CallbackQuery, state: FSMContext):
    duration = int(callback.data.split('_')[1])
    data = await state.get_data()

    test_code = await db.create_test(
        owner_user_id=callback.from_user.id,
        question_file_id=data.get('file_id'),
        question_file_type=data.get('file_type'),
        answer_key=data.get('answers'),
        duration_minutes=duration
    )

    await callback.message.delete()
    duration_text = f"{duration} daqiqa" if duration > 0 else "Cheklanmagan"

    await callback.message.answer(
        f"<b>✅ Test muvaffaqiyatli yaratildi!</b>\n\n"
        f"<b>🔑 Test kodi:</b> <code>{test_code}</code> (bu kodni nusxalab, o'quvchilarga tarqating)\n"
        f"<b>⏳ Har bir o'quvchi uchun vaqt:</b> {duration_text}\n\n"
        f"Natijalarni ko'rish va testni yakunlash uchun "
        f"«📋 Mening Testlarim» bo'limidan foydalaning.",
        # --- BU YERDA XATO BOR EDI. TUZATILDI ---
        reply_markup=main_menu_keyboard(callback.from_user.id)
    )
    await callback.answer()
    await state.clear()
