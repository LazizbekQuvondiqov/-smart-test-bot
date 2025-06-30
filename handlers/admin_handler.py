# handlers/admin_handler.py

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import asyncio
import logging

import database as db
from config import SUPER_ADMINS
from keyboards import (
    admin_panel_keyboard, main_menu_keyboard, confirm_broadcast_keyboard,
    BTN_ADMIN_PANEL, BTN_BACK, BTN_ADD_CHANNEL, BTN_DEL_CHANNEL,
    BTN_CHANNEL_LIST, BTN_START_CONTEST, BTN_CLEAR_CONTEST, BTN_BROADCAST
)

router = Router()
# Bu routerdagi barcha handlerlar faqat Super Adminlar uchun ishlaydi
router.message.filter(F.from_user.id.in_(SUPER_ADMINS))

class BroadcastState(StatesGroup):
    waiting_for_content = State()
    confirming = State()


# --- Asosiy admin tugmalari va universal bekor qilish ---

@router.message(F.text == BTN_ADMIN_PANEL)
async def admin_panel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Salom, Super Admin! Maxsus buyruqlar panelidasiz.", reply_markup=admin_panel_keyboard())

@router.message(F.text == BTN_BACK)
async def back_to_main_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard(message.from_user.id))

# --- KANAL BOSHQARUVI (Buyruqlar bilan, sodda usulda) ---
@router.message(F.text == BTN_ADD_CHANNEL)
async def ask_add_channel(message: Message):
    await message.answer("Kanal qo'shish uchun quyidagi formatda yozing:\n\n`/add @kanal_manzili`", parse_mode="Markdown")


# --- O'ZGARISH: `add_channel_handler` funksiyasi to'liq yangilandi ---
@router.message(Command("add"))
async def add_channel_handler(message: Message, bot: Bot):
    try:
        channel_username_str = message.text.split()[1]
        if not channel_username_str.startswith("@"):
            raise ValueError()
    except (IndexError, ValueError):
        await message.reply("Xato: Buyruq formati noto'g'ri.\nTo'g'ri format: `/add @kanal_manzili`")
        return

    try:
        chat = await bot.get_chat(channel_username_str)

        username = None
        invite_link = None

        # Kanal turiga qarab havola olish
        if chat.username:
            # 1-Holat: Kanal OCHIQ (Public)
            username = chat.username
            if await db.add_channel(chat.id, username=username):
                 await message.answer(f"✅ Ochiq kanal (`{chat.title}`) ro'yxatiga qo'shildi.")
            else:
                 await message.answer(f"Bu kanal (`{chat.title}`) allaqachon bor edi. Ma'lumotlari yangilandi.")
        else:
            # 2-Holat: Kanal XUSUSIY (Private)
            # Bot kanalda admin bo'lishi va 'invite users' huquqiga ega bo'lishi SHART!
            invite_link_obj = await bot.create_chat_invite_link(chat.id)
            invite_link = invite_link_obj.invite_link
            if await db.add_channel(chat.id, invite_link=invite_link):
                await message.answer(f"✅ Xususiy kanal (`{chat.title}`) ro'yxatiga qo'shildi va taklif havolasi yaratildi.")
            else:
                await message.answer(f"Bu kanal (`{chat.title}`) allaqachon bor edi. Taklif havolasi yangilandi.")

    except Exception as e:
        logging.error(f"Kanal qo'shishda xato: {e}")
        await message.answer(
            f"Xatolik yuz berdi!\n\n"
            f"<b>Sabab:</b> {e}\n\n"
            f"Iltimos, quyidagilarga ishonch hosil qiling:\n"
            f"1. Bot kanalda admin.\n"
            f"2. Xususiy kanal uchun botga <b>'Foydalanuvchilarni taklif qilish'</b> huquqi berilgan."
        )


@router.message(F.text == BTN_DEL_CHANNEL)
async def ask_del_channel(message: Message):
    await message.answer("Kanalni o'chirish uchun quyidagi formatda yozing:\n\n`/del @kanal_manzili` yoki `/del KANAL_ID`", parse_mode="Markdown")

@router.message(Command("del"))
async def delete_channel_handler(message: Message, bot: Bot):
    try:
        # Endi ID yoki username orqali o'chirishni qo'llab-quvvatlaymiz
        channel_identifier = message.text.split()[1]
    except (IndexError, ValueError):
        await message.reply("Xato: Buyruq formati noto'g'ri.\nTo'g'ri format: `/del @kanal_manzili` yoki `/del KANAL_ID`")
        return

    try:
        # ID orqali o'chirishga harakat qilamiz, agar raqam bo'lsa
        if channel_identifier.lstrip('-').isdigit():
            chat_id_to_delete = int(channel_identifier)
            # Botni o'sha kanaldan o'chirib qo'yish shart emas, lekin xohlasangiz mumkin
            # await bot.leave_chat(chat_id_to_delete)
        else:
            # Username orqali ID ni olamiz
            chat = await bot.get_chat(channel_identifier)
            chat_id_to_delete = chat.id

        if await db.delete_channel(chat_id_to_delete):
            await message.answer(f"✅ Kanal (`{channel_identifier}`) ro'yxatdan o'chirildi.")
        else:
            await message.answer("❌ Bu kanal ro'yxatda topilmadi.")
    except Exception as e:
        await message.answer(f"Xatolik: {e}")


# --- O'ZGARISH: `channels_list_handler` funksiyasi yangilandi ---
@router.message(F.text == BTN_CHANNEL_LIST)
async def channels_list_handler(message: Message, bot: Bot):
    channels = await db.get_channels()
    if not channels:
        await message.answer("Majburiy obuna uchun kanallar qo'shilmagan.")
        return

    text = "Majburiy obuna uchun kanallar ro'yxati:\n\n"
    for i, (channel_id, username, invite_link) in enumerate(channels, 1):
        try:
            chat = await bot.get_chat(channel_id)
            link = f"https://t.me/{username}" if username else invite_link
            text += f"{i}. <b>{chat.title}</b>\n"
            text += f"   - ID: <code>{channel_id}</code>\n"
            text += f"   - Havola: {link}\n\n"
        except Exception:
            text += f"{i}. <b>Noma'lum kanal</b>\n"
            text += f"   - ID: <code>{channel_id}</code> (ehtimol bot kanaldan chiqarilgan)\n\n"

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


# --- KONKURS BOSHQARUVI ---
@router.message(F.text == BTN_START_CONTEST)
async def start_contest_handler(message: Message):
    await db.clear_all_referral_counts()
    await message.answer("✅ Yangi referral konkursi boshlandi! Barcha foydalanuvchilarning ballari 0 ga tushirildi.")

@router.message(F.text == BTN_CLEAR_CONTEST)
async def clear_contest_handler(message: Message):
    await db.clear_all_referral_counts()
    await message.answer("✅ Konkurs statistikasi tozalandi.")

# --- OMMOBIY XABAR YUBORISH (PROGRESS BAR BILAN) ---
@router.message(F.text == BTN_BROADCAST)
async def start_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Barcha foydalanuvchilarga yuboriladigan xabarni (reklamani) yuboring.\n"
        "Bu matn, rasm, video yoki boshqa turdagi xabar bo'lishi mumkin."
    )
    await state.set_state(BroadcastState.waiting_for_content)

@router.message(BroadcastState.waiting_for_content)
async def get_broadcast_content(message: Message, state: FSMContext):
    await state.update_data(
        content_message_id=message.message_id,
        chat_id=message.chat.id
    )
    users_count = await db.get_active_users_count()

    await message.answer(
        f"Xabar qabul qilindi. Bu xabarni **{users_count} ta** foydalanuvchiga yuborishni tasdiqlaysizmi?",
        reply_markup=confirm_broadcast_keyboard()
    )
    await state.set_state(BroadcastState.confirming)

@router.callback_query(F.data == "confirm_broadcast_send", BroadcastState.confirming)
async def send_broadcast_confirmed(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer("Yuborish boshlanmoqda...", show_alert=False)

    data = await state.get_data()
    message_id_to_send = data.get('content_message_id')
    from_chat_id = data.get('chat_id')
    await state.clear()

    status_message = await callback.message.edit_text(
        f"Xabar yuborish boshlandi...",
        reply_markup=None
    )

    if not message_id_to_send:
        await callback.message.answer("Xatolik: Yuboriladigan xabar topilmadi. Qaytadan urinib ko'ring.", reply_markup=admin_panel_keyboard())
        return

    user_ids = await db.get_all_user_ids()
    total_users = len(user_ids)
    sent_count = 0
    failed_count = 0
    last_update_text = ""

    for i, user_id in enumerate(user_ids, 1):
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id_to_send)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            logging.error(f"Failed to send message to {user_id}: {e}")

        if i % 25 == 0 or i == total_users:
            percentage = (i / total_users) * 100
            progress_text = f"⏳ Yuborilmoqda: {percentage:.1f}% ({i}/{total_users})"

            if progress_text != last_update_text:
                try:
                    await status_message.edit_text(progress_text)
                    last_update_text = progress_text
                except TelegramBadRequest:
                    pass

    await status_message.delete()
    await callback.message.answer(
        f"✅ Xabar yuborish yakunlandi!\n\n"
        f"🟢 Yuborildi: {sent_count} ta foydalanuvchiga\n"
        f"🔴 Xatolik: {failed_count} ta foydalanuvchiga",
        reply_markup=admin_panel_keyboard()
    )

@router.callback_query(F.data == "confirm_broadcast_cancel", BroadcastState.confirming)
async def cancel_broadcast_confirmed(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi.", show_alert=True)
    await callback.message.edit_text(
        "Xabar yuborish bekor qilindi.",
        reply_markup=None
    )
