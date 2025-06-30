# config.py faylining yangi, to'liq ko'rinishi

import os
from dotenv import load_dotenv

# .env faylidagi o'zgaruvchilarni tizimga yuklaydi
load_dotenv()

# Bot tokenini .env faylidan olish
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Ma'lumotlar bazasi nomini .env faylidan olish
DB_NAME = os.getenv("DB_NAME")

# Super Adminlar ro'yxatini .env faylidan olish
# Avval string (matn) sifatida olinadi, keyin sonlar ro'yxatiga o'tkaziladi
admins_str = os.getenv("SUPER_ADMINS", "") # Agar topilmasa, bo'sh satr oladi
if admins_str:
    SUPER_ADMINS = [int(admin_id.strip()) for admin_id in admins_str.split(',')]
else:
    SUPER_ADMINS = []

# Dastur ishlashi uchun muhim o'zgaruvchilarni tekshirish
if not BOT_TOKEN:
    raise ValueError("Xatolik: BOT_TOKEN o'zgaruvchisi .env faylida topilmadi yoki bo'sh!")
if not DB_NAME:
    raise ValueError("Xatolik: DB_NAME o'zgaruvchisi .env faylida topilmadi yoki bo'sh!")
if not SUPER_ADMINS:
    print("Ogohlantirish: SUPER_ADMINS ro'yxati .env faylida topilmadi yoki bo'sh!")
