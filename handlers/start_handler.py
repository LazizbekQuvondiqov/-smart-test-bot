# handlers/start_handler.py

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging
import asyncio
import io
from datetime import timedelta
import openpyxl
from openpyxl.styles import Font, Alignment

import database as db
from keyboards import (
    main_menu_keyboard, share_keyboard, my_tests_keyboard,
    test_management_keyboard, confirm_close_test_keyboard,
    show_error_details_keyboard, subscribe_keyboard
)
from config import SUPER_ADMINS

router = Router()

async def generate_excel_report(test_code: int, results: list, total_questions: int) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f"Test #{test_code} Natijalari"
    headers = ["№", "F.I.O", "Telegram ID", "To'g'ri javoblar", "Natija (%)", "Sarflangan vaqt (MM:SS)"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    for i, row in enumerate(results, 1):
        user_id, full_name, score, start_time, submitted_at = row
        percentage = f"{(score / total_questions) * 100:.1f}%" if total_questions > 0 else "0.0%"
        time_taken_seconds = submitted_at - start_time
        time_taken_formatted = str(timedelta(seconds=time_taken_seconds)).split('.')[0][2:]
        sheet.append([i, full_name, user_id, f"{score}/{total_questions}", percentage, time_taken_formatted])
    for column_cells in sheet.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = length + 2
    file_stream = io.BytesIO()
    workbook.save(file_stream)
    file_stream.seek(0)
    return file_stream.getvalue()

async def check_subscription(user_id: int, bot: Bot):
    channels = await db.get_channels()
    if not channels: return True
    for channel_id, username, invite_link in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status.lower() not in ['member', 'administrator', 'creator']: return False
        except Exception as e:
            logging.error(f"Subscription check error for user {user_id} in channel {channel_id}: {e}")
            return False
    return True

async def give_referral_bonus(user_id: int, bot: Bot):
    referrer_id = await db.get_referred_by(user_id)
    if referrer_id:
        await db.update_referral_count(referrer_id)
        new_user_name = await db.get_user_fullname(user_id) or f"ID: {user_id}"
        try:
            await bot.send_message(chat_id=referrer_id, text=f"🎉 Tabriklaymiz! Sizning taklifingiz orqali <b>{new_user_name}</b> botga a'zo bo'ldi.\n\nHisobingizga +1 ball qo'shildi!")
        except Exception as e:
            logging.error(f"Referral xabarini yuborishda xato: {e}")

async def show_welcome_message(message: Message, user_id: int):
    await message.answer(f"🎉 Assalomu alaykum, <b>{message.from_user.full_name}</b>!\n\n<b>SmartTest</b> botiga xush kelibsiz!", reply_markup=main_menu_keyboard(user_id))

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referred_by_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if referred_by_id == message.from_user.id: referred_by_id = None
    is_new_user = await db.add_user(user_id=message.from_user.id, username=message.from_user.username, full_name=message.from_user.full_name, referred_by_id=referred_by_id)
    if await check_subscription(message.from_user.id, bot):
        if is_new_user: await give_referral_bonus(message.from_user.id, bot)
        await show_welcome_message(message, message.from_user.id)
    else:
        channels = await db.get_channels()
        kb = await subscribe_keyboard(channels)
        await message.answer("❗️ Botdan to'liq foydalanish uchun, iltimos, quyidagi kanallarga a'zo bo'ling va «✅ A'zo bo'ldim, Tekshirish» tugmasini bosing.", reply_markup=kb)

@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery, bot: Bot):
    await callback.answer(text="Tekshirilmoqda...", show_alert=False)
    if await check_subscription(callback.from_user.id, bot):
        referrer_id = await db.get_referred_by(callback.from_user.id)
        if referrer_id: await give_referral_bonus(callback.from_user.id, bot)
        await callback.message.delete()
        await show_welcome_message(callback.message, callback.from_user.id)
    else:
        try: await callback.answer("❌ Kechirasiz, siz hali barcha kanallarga a'zo bo'lmadingiz. Iltimos, tekshirib ko'ring.", show_alert=True)
        except TelegramBadRequest: pass

@router.message(F.text == "🔗 Do'st Taklif Qilish")
async def referral_handler(message: Message):
    count = await db.get_user_referral_count(message.from_user.id)
    bot_info = await message.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"Siz taklif qilgan do'stlaringiz soni: <b>{count} ta</b>.\n\nQuyidagi havola orqali do'stlaringizni botga taklif qiling va reytingda yuqorilang!", reply_markup=share_keyboard(referral_link))

@router.message(F.text == "🏆 Reyting")
async def public_contest_stats_handler(message: Message):
    stats = await db.get_contest_stats()
    if not stats: await message.answer("Hozircha reytingda hech kim yo'q. Birinchi bo'ling!"); return
    text = "🏆 <b>Eng faol foydalanuvchilar (TOP-10)</b>:\n\n"
    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, (full_name, count) in enumerate(stats):
        emoji = emojis[i] if i < len(emojis) else f"{i+1}."
        text += f"{emoji} {full_name} - <b>{count}</b> ta do'st\n"
    await message.answer(text)

@router.message(Command("help"))
async def help_command_handler(message: Message):
    user_id = message.from_user.id
    if user_id in SUPER_ADMINS: text = ("👑 <b>Admin uchun qo'llanma:</b>\n\n"
                                        "`/add @kanal` - Majburiy obuna kanalini qo'shish.\n"
                                        "`/del @kanal` - Kanalni o'chirish.\n"
                                        "Qolgan amallar admin panelidagi tugmalar orqali bajariladi.")
    else: text = ("ℹ️ <b>Foydalanuvchi uchun qo'llanma:</b>\n\n"
                  "Botdan foydalanish uchun menyudagi tugmalardan foydalaning:\n"
                  "<b>✍️ Yangi Test Yaratish</b> - O'zingizning shaxsiy testingizni yaratish.\n"
                  "<b>✅ Test Yechish</b> - Boshqalarning test kodini kiritib, test yechish.\n"
                  "<b>📋 Mening Testlarim</b> - Siz yaratgan testlarni boshqarish.\n"
                  "<b>🔗 Do'st Taklif Qilish</b> - Botga do'stlaringizni taklif qilib, reytingda qatnashish.")
    await message.answer(text)

@router.message(F.text == "📋 Mening Testlarim")
async def my_tests_handler(message: Message):
    tests = await db.get_user_tests(message.from_user.id)
    if not tests: await message.answer("Sizda hozirda aktiv testlar mavjud emas."); return
    await message.answer("Siz yaratgan aktiv testlar ro'yxati:", reply_markup=await my_tests_keyboard(tests))

@router.callback_query(F.data.startswith("view_test_"))
async def view_test_details(callback: CallbackQuery):
    test_code = int(callback.data.split("_")[2])
    text = f"Tanlangan test kodi: <code>{test_code}</code>\n\nQuyidagi amallardan birini tanlang:"
    await callback.message.edit_text(text, reply_markup=test_management_keyboard(test_code))
    await callback.answer()

@router.callback_query(F.data == "back_to_test_list")
async def back_to_test_list(callback: CallbackQuery):
    await callback.message.delete()
    await my_tests_handler(callback.message)
    await callback.answer()

@router.callback_query(F.data.startswith("participants_"))
async def show_participants_count(callback: CallbackQuery):
    try:
        test_code = int(callback.data.split("_")[1])
        count = await db.get_test_participant_count(test_code)
        await callback.answer(f"Test #{test_code}\nIshtirokchilar soni: {count} ta", show_alert=True)
    except (ValueError, IndexError):
        await callback.answer("Xatolik: Test kodi topilmadi.", show_alert=True)

@router.callback_query(F.data.startswith("confirm_close_"))
async def confirm_close_handler(callback: CallbackQuery):
    try:
        test_code = int(callback.data.split("_")[2])
        text = (f"<b>DIQQAT!</b>\n\nSiz <code>{test_code}</code>-sonli testni yakunlamoqchisiz. "
                "Bu amalni orqaga qaytarib bo'lmaydi. Barcha ishtirokchilarga natijalar yuboriladi va sizga Excel-hisobot taqdim etiladi.")
        await callback.message.edit_text(text, reply_markup=confirm_close_test_keyboard(test_code))
        await callback.answer()
    except (ValueError, IndexError):
        await callback.answer("Xatolik: Test kodi topilmadi.", show_alert=True)

async def send_results_and_close_test(callback: CallbackQuery, bot: Bot, test_code: int):
    results, owner_id, answer_key = await db.get_test_results(test_code)
    if results is None:
        await callback.answer(f"❌ Test #{test_code} topilmadi.", show_alert=True)
        return 0, False
    if callback.from_user.id != owner_id and callback.from_user.id not in SUPER_ADMINS:
        await callback.answer("❌ Siz bu testni yakunlay olmaysiz.", show_alert=True)
        return 0, False
    total_questions = len(answer_key)
    sent_count = 0
    top_winners = results[:3]
    other_participants = results[3:]

    # 1. G'oliblarga sertifikat va natijalarni yuborish
    for i, winner_data in enumerate(top_winners):
        place = i + 1
        user_id, full_name, score, _, _ = winner_data
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        if place == 1:
            photo_path = "1-o'rin.png"
            caption_title = "🏆 TABRIKLAYMIZ, SIZ MUTLAQ G'OLIBSIZ! 🏆"
        elif place == 2:
            photo_path = "2-o'rin.png"
            caption_title = "🥈 TABRIKLAYMIZ, SIZ 2-O'RIN SOVRINDORISIZ! 🥈"
        else:
            photo_path = "3-o'rin.png"
            caption_title = "🥉 TABRIKLAYMIZ, SIZ 3-O'RIN SOVRINDORISIZ! 🥉"
        try:
            certificate_photo = FSInputFile(photo_path)
            caption_text = (f"<b>{caption_title}</b>\n\n"
                            f"Siz <b>Test #{test_code}</b> da faxrli <b>{place}-o'rinni</b> egalladingiz!\n\n"
                            f"Natijangiz: <b>{score}/{total_questions}</b> ({percentage:.1f}%)")
            await bot.send_photo(chat_id=user_id, photo=certificate_photo, caption=caption_text, reply_markup=show_error_details_keyboard(test_code))
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"{place}-o'rin g'olibiga ({user_id}) sertifikat yuborishda xato: {e}")

    # 2. Qolgan ishtirokchilarga oddiy natija yuborish
    for participant_data in other_participants:
        user_id, full_name, score, _, _ = participant_data
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        result_text = (f"<b>Test #{test_code} Natijasi</b>\n\nIshtirokchi: <b>{full_name}</b>\nTo'g'ri javoblar soni: <b>{score} / {total_questions}</b>\nO'zlashtirish: <b>{percentage:.1f}%</b>")
        try:
            await bot.send_message(user_id, result_text, reply_markup=show_error_details_keyboard(test_code))
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception: pass

    # 3. Test egasiga Excel hisobotini yuborish
    excel_sent = False
    if results:
        try:
            excel_bytes = await generate_excel_report(test_code, results, total_questions)
            report_file = BufferedInputFile(excel_bytes, filename=f"test_{test_code}_natijalar.xlsx")
            await bot.send_document(chat_id=owner_id, document=report_file, caption=f"✅ <b>Test #{test_code}</b> uchun yakuniy hisobot.")
            excel_sent = True
        except Exception as e:
            logging.error(f"Excel hisobotini yuborishda xato: {e}")
            await bot.send_message(owner_id, f"❗️ Test #{test_code} uchun Excel-hisobotni yaratishda xatolik yuz berdi.")
    await db.close_test(test_code)
    return sent_count, excel_sent

@router.callback_query(F.data.startswith("close_test_"))
async def close_test_handler(callback: CallbackQuery, bot: Bot):
    try:
        test_code = int(callback.data.split("_")[2])
        await callback.message.edit_text(f"⏳ Test #{test_code} yakunlanmoqda... Natijalar yuborilmoqda.")
        sent_count, excel_sent = await send_results_and_close_test(callback, bot, test_code)
        final_text = f"✅ Test #{test_code} muvaffaqiyatli yakunlandi.\n\nNatijalar {sent_count} ta ishtirokchiga yuborildi."
        if excel_sent: final_text += "\n\n📊 Batafsil hisobot (Excel) sizga shaxsiy xabar qilib yuborildi."
        await callback.message.edit_text(final_text)
        await callback.answer("Test yakunlandi!", show_alert=True)
    except (ValueError, IndexError):
        await callback.answer("Xatolik: Test kodi topilmadi.", show_alert=True)


# --- YAKUNIY O'ZGARISH: BU FUNKSIYA BU YERGA KO'CHIRILDI VA TUZATILDI ---
@router.callback_query(F.data.startswith("show_errors_"))
async def show_error_details(callback: CallbackQuery):
    try:
        test_code = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Xatolik: Test kodi topilmadi.", show_alert=True)
        return

    user_id = callback.from_user.id
    details = await db.get_user_answer_details(test_code, user_id)

    if not details:
        await callback.answer("❌ Sizning bu testdagi javoblaringiz topilmadi.", show_alert=True)
        return

    correct_key, user_answers = details
    analysis_text = f"<b>Test #{test_code} uchun tahlil:</b>\n\n"
    total_score = 0

    for i in range(len(correct_key)):
        user_ans = user_answers[i].upper() if i < len(user_answers) else '?'
        corr_ans = correct_key[i].upper()

        if user_ans == corr_ans:
            analysis_text += f"✅ {i+1}-savol: {user_ans} (To'g'ri)\n"
            total_score += 1
        else:
            analysis_text += f"❌ {i+1}-savol: Sizning javob {user_ans} (To'g'ri: {corr_ans})\n"

    percentage = (total_score / len(correct_key)) * 100 if len(correct_key) > 0 else 0
    analysis_text += f"\n📊 <b>Umumiy natija: {total_score} ta to'g'ri ({percentage:.1f}%)</b>"

    try:
        # Rasm bilan kelgan xabarni tahrirlash uchun maxsus metod kerak
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=analysis_text,
                reply_markup=None # Tugmani olib tashlash
            )
        else:
            # Oddiy matnli xabarni tahrirlash
            await callback.message.edit_text(
                text=analysis_text,
                reply_markup=None # Tugmani olib tashlash
            )

        await callback.answer() # Foydalanuvchiga "Bajarildi" degan bildirishnoma ko'rsatish (jim)

    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            await callback.answer("Siz allaqachon xatolaringizni ko'rgansiz.")
        else:
            logging.error(f"Xatolarni ko'rsatishda Telegram xatosi: {e}")
            await callback.answer("Xabarni tahrirlashda xatolik yuz berdi.", show_alert=True)
    except Exception as e:
        logging.error(f"Kutilmagan xato (show_errors): {e}")
        await callback.answer("Kutilmagan xatolik yuz berdi.", show_alert=True)
