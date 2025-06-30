# handlers/test_process.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import time, datetime, re, asyncio
import logging

import database as db
from keyboards import show_error_details_keyboard

router = Router()

class TestAnsweringStates(StatesGroup):
    waiting_for_code = State()

@router.message(F.text == "✅ Test Yechish")
async def start_answering_test(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Marhamat, o'qituvchingiz bergan test kodini kiriting:", reply_markup=None)
    await state.set_state(TestAnsweringStates.waiting_for_code)

@router.message(TestAnsweringStates.waiting_for_code, F.text)
async def process_test_code(message: Message, state: FSMContext):
    try:
        test_code = int(message.text)
    except ValueError:
        await message.answer("❌ Test kodi faqat raqamlardan iborat bo'lishi kerak. Iltimos, qayta kiriting.")
        return

    test_data = await db.get_test_by_code(test_code)
    if not test_data:
        await message.answer("❌ Bunday kodli test topilmadi. Kodni tekshirib, qayta urinib ko'ring.")
        await state.clear()
        return

    (test_id, file_id, file_type, duration,
     owner_id, answer_key, status) = test_data

    if status == 'closed':
        await message.answer("❌ Kechirasiz, bu test yakunlangan va javob qabul qilinmaydi.")
        await state.clear()
        return

    if await db.has_user_answered(message.from_user.id, test_id):
        await message.answer("❗️ Siz bu testga allaqachon javob topshirgansiz!")
        await state.clear()
        return

    if not await db.start_user_session(message.from_user.id, test_id):
        await message.answer("Siz bu testni allaqachon boshlagansiz! Iltimos, javoblaringizni yuboring.")
        await state.clear()
        return

    await state.clear()
    duration_text = f"Testni yechish uchun <b>{duration} daqiqa</b> vaqtingiz bor." if duration > 0 else "Vaqtingiz cheklanmagan."
    end_time_text = ""
    if duration > 0:
        end_time = datetime.datetime.now() + datetime.timedelta(minutes=duration)
        end_time_text = f"\n<b>Sizning shaxsiy vaqtingiz {end_time.strftime('%H:%M')} da tugaydi.</b>"

    try:
        if file_type == 'photo':
            await message.answer_photo(file_id)
        elif file_type == 'document':
            await message.answer_document(file_id)
        else:
            await message.answer("❗️ Test faylini yuborishda xatolik yuz berdi. Iltimos, test egasiga murojaat qiling.")
    except Exception as e:
        logging.error(f"Fayl (ID: {file_id}) yuborishda xato: {e}")
        await message.answer("❗️ Test faylini yuborishda xatolik yuz berdi.")

    await message.answer(
        f"<b>Test #{test_code} boshlandi.</b>\n\n"
        f"⏳ {duration_text}{end_time_text}\n\n"
        f"Diqqat! Javoblaringizni quyidagi formatda yuboring (javoblar orasida bo'sh joy qoldirmang):\n"
        f"👉 <code>{test_code}*abcd...</code>"
    )

@router.message(F.text.regexp(r'^\d+\*.+'))
async def process_test_answers(message: Message):
    try:
        test_code_str, user_answers_raw = message.text.split('*', 1)
        test_code = int(test_code_str)
    except ValueError:
        return

    test_data = await db.get_test_by_code(test_code)
    if not test_data:
        await message.reply("Siz kiritgan test kodi mavjud emas.")
        return

    (test_id, _, _, duration, _,
     correct_answers_key, status) = test_data

    if status == 'closed':
        await message.answer("❌ Kechirasiz, siz javob yuborguningizcha test yakunlandi.")
        return

    session = await db.get_user_session(message.from_user.id, test_id)
    if not session:
        await message.answer("Siz bu testni boshlamagansiz yoki vaqtingiz tugagan. Iltimos, kodni qayta kiriting.")
        return

    session_id, start_time = session

    if duration > 0 and (time.time() - start_time) > (duration * 60):
        await message.answer("❌ Kechirasiz, sizga ajratilgan vaqt tugadi...")
        return

    user_answers_clean = re.sub(r'[\d\s\W_]+', '', user_answers_raw).lower()
    total_questions = len(correct_answers_key)

    if len(user_answers_clean) > total_questions:
         user_answers_clean = user_answers_clean[:total_questions]
    elif len(user_answers_clean) < total_questions:
         await message.answer(
            f"❗️ <b>Diqqat! Xatolik!</b>\n\n"
            f"Testda jami <b>{total_questions} ta</b> savol mavjud.\n"
            f"Siz esa <b>{len(user_answers_clean)} ta</b> javob yubordingiz.\n\n"
            f"Iltimos, javoblarni to'liq (<code>{test_code}*javoblar...</code>) formatida qayta yuboring."
        )
         return

    score = sum(1 for i in range(total_questions) if i < len(user_answers_clean) and user_answers_clean[i] == correct_answers_key[i])

    if not await db.save_user_answer(session_id, message.from_user.id, score, user_answers_clean):
        await message.answer("Siz bu testga allaqachon javob bergansiz.")
        return

    await message.answer("✅ <b>Javobingiz qabul qilindi!</b>\n\nBarcha natijalar test yakunlangandan so'ng e'lon qilinadi.")

# "show_error_details" funksiyasi bu yerdan olib tashlandi va start_handler.py ga ko'chirildi.
