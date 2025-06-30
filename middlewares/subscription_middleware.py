# middlewares/subscription_middleware.py

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import Update, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import logging

import database as db
from keyboards import subscribe_keyboard
from config import SUPER_ADMINS

async def check_subscription(user_id: int, bot: Bot):
    """
    Foydalanuvchining majburiy kanallarga obuna bo'lganligini tekshiradi.
    Yangi baza sxemasini (id, username, link) qo'llab-quvvatlaydi.
    """
    try:
        channels = await db.get_channels()
        if not channels:
            return True # Agar majburiy kanallar bo'lmasa, har doim True

        for channel_id, username, invite_link in channels:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status.lower() not in ['member', 'administrator', 'creator']:
                logging.warning(f"User {user_id} is NOT subscribed to channel {channel_id}. Status: {member.status}")
                return False
        return True
    except Exception as e:
        logging.error(f"Error during subscription check for user {user_id}: {e}")
        return False


class SubscriptionMiddleware(BaseMiddleware):
    # --- O'ZGARISH: `__init__` metodi qaytarildi ---
    # Bu `main.py` dagi `SubscriptionMiddleware(bot=bot)` chaqiruviga mos keladi.
    def __init__(self, bot: Bot):
        self.bot = bot

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        user_event = event.message or event.callback_query

        if not user_event:
            return await handler(event, data)

        chat = user_event.message.chat if isinstance(user_event, CallbackQuery) else user_event.chat
        if chat.type != 'private':
            return await handler(event, data)

        user_id = user_event.from_user.id

        if user_id in SUPER_ADMINS:
            return await handler(event, data)

        if isinstance(user_event, Message) and user_event.text and user_event.text.startswith("/start"):
             return await handler(event, data)
        if isinstance(user_event, CallbackQuery) and user_event.data == "check_subscription":
            return await handler(event, data)

        # --- O'ZGARISH: bot obyektini `self.bot` dan olamiz ---
        if not await check_subscription(user_id, self.bot):
            channels = await db.get_channels()
            if not channels:
                 return await handler(event, data)

            kb = await subscribe_keyboard(channels)
            text = "❗️ Botdan to'liq foydalanish uchun, iltimos, quyidagi kanallarga a'zo bo'ling va «✅ A'zo bo'ldim, Tekshirish» tugmasini bosing."

            if isinstance(user_event, CallbackQuery):
                await user_event.answer(
                    "❗️ Botdan to'liq foydalanish uchun, iltimos, kanallarga obuna bo'ling.",
                    show_alert=True
                )
            else:
                try:
                    await user_event.answer(text, reply_markup=kb)
                except TelegramBadRequest:
                    pass

            return

        return await handler(event, data)
