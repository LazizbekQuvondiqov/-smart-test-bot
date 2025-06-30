# main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database import setup_database, delete_old_tests
from handlers import start_handler, admin_handler, test_creation, test_process
from middlewares.subscription_middleware import SubscriptionMiddleware

async def scheduled_test_cleanup():
    await delete_old_tests()

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    await setup_database()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middleware'ni ro'yxatdan o'tkazish
    # Update'lar routerlarga yetib borishidan oldin bu yerdan o'tadi
    dp.update.middleware(SubscriptionMiddleware(bot=bot))

    # Routerlarni ulash
    dp.include_router(start_handler.router)
    dp.include_router(admin_handler.router)
    dp.include_router(test_creation.router)
    dp.include_router(test_process.router)

    # Rejalashtiruvchini sozlash
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(scheduled_test_cleanup, trigger='interval', days=1, misfire_grace_time=3600)
    scheduler.start()

    # Botni ishga tushirishdan oldin eski update'larni o'chirish
    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
