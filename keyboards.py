# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from urllib.parse import quote
from config import SUPER_ADMINS

BTN_CREATE_TEST = "✍️ Yangi Test Yaratish"
BTN_SOLVE_TEST = "✅ Test Yechish"
BTN_MY_TESTS = "📋 Mening Testlarim"
BTN_INVITE_FRIEND = "🔗 Do'st Taklif Qilish"
BTN_RATING = "🏆 Reyting"
BTN_ADMIN_PANEL = "👑 Admin Paneli"

def main_menu_keyboard(user_id: int):
    kb = [
        [KeyboardButton(text=BTN_CREATE_TEST), KeyboardButton(text=BTN_SOLVE_TEST)],
        [KeyboardButton(text=BTN_MY_TESTS), KeyboardButton(text=BTN_INVITE_FRIEND)],
        [KeyboardButton(text=BTN_RATING)]
    ]
    if user_id in SUPER_ADMINS:
        kb.append([KeyboardButton(text=BTN_ADMIN_PANEL)])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Kerakli bo'limni tanlang...")


BTN_ADD_CHANNEL = "➕ Kanal Qo'shish"
BTN_DEL_CHANNEL = "🗑️ Kanal O'chirish"
BTN_CHANNEL_LIST = "📋 Kanallar Ro'yxati"
BTN_START_CONTEST = "🚀 Konkurs Boshlash"
BTN_CLEAR_CONTEST = "🔄 Konkursni Tozalash"
BTN_BROADCAST = "📢 Ommaviy Xabar Yuborish"
BTN_BACK = "⬅️ Ortga"

def admin_panel_keyboard():
    kb = [
        [KeyboardButton(text=BTN_ADD_CHANNEL), KeyboardButton(text=BTN_DEL_CHANNEL)],
        [KeyboardButton(text=BTN_CHANNEL_LIST)],
        [KeyboardButton(text=BTN_START_CONTEST), KeyboardButton(text=BTN_CLEAR_CONTEST)],
        [KeyboardButton(text=BTN_BROADCAST)],
        [KeyboardButton(text=BTN_BACK)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Admin buyrug'ini tanlang...")

def share_keyboard(referral_link: str):
    share_text = (
        "Assalomu alaykum! 👋\n\n"
        "Men o'qituvchilar va o'quvchilar uchun ajoyib bo'lgan **SmartTest** botini topdim. Bu yerda testlarni oson yaratish va yechish mumkin!\n\n"
        "Eng qizig'i, do'stlarni taklif qilib, reytingda yuqorilash va sovrinlar yutib olish imkoniyati bor! 🚀\n\n"
        "Quyidagi havola orqali botga kiring va siz ham ishtirok eting 👇"
    )
    encoded_text = quote(f"{share_text}\n\n{referral_link}")
    kb = [[InlineKeyboardButton(
        text="🚀 Do'stlarga Ulashish",
        url=f"https://t.me/share/url?url={encoded_text}"
    )]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# --- O'ZGARISH: `subscribe_keyboard` funksiyasi to'liq yangilandi ---
async def subscribe_keyboard(channels):
    buttons = []
    # `db.get_channels()` endi (id, username, link) ko'rinishidagi ro'yxat qaytaradi
    for i, (channel_id, username, invite_link) in enumerate(channels, 1):
        link = ""
        # Eng ishonchli usuldan boshlab tekshiramiz
        if username:
            # Agar username bo'lsa, bu eng barqaror havola
            link = f"https://t.me/{username}"
        elif invite_link:
            # Agar username bo'lmasa (xususiy kanal), tayyor taklif havolasidan foydalanamiz
            link = invite_link

        # Agar qandaydir sabab bilan link bo'lmasa, tugma qo'shilmaydi
        if link:
            buttons.append([InlineKeyboardButton(text=f"📢 {i}-Kanalga A'zo Bo'lish", url=link)])

    buttons.append([InlineKeyboardButton(text="✅ A'zo bo'ldim, Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def test_duration_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="30 daqiqa", callback_data="duration_30"),
            InlineKeyboardButton(text="60 daqiqa", callback_data="duration_60"),
            InlineKeyboardButton(text="90 daqiqa", callback_data="duration_90"),
        ],
        [InlineKeyboardButton(text="♾️ Vaqt Cheklanmagan", callback_data="duration_0")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def show_error_details_keyboard(test_code: int):
    kb = [[InlineKeyboardButton(text="🔑 Xatolarimni Ko'rish", callback_data=f"show_errors_{test_code}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def confirm_broadcast_keyboard():
    kb = [[
        InlineKeyboardButton(text="✅ Ha, Yuborilsin!", callback_data="confirm_broadcast_send"),
        InlineKeyboardButton(text="❌ Bekor Qilish", callback_data="confirm_broadcast_cancel")
    ]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def my_tests_keyboard(tests: list):
    buttons = []
    for test in tests:
        test_code = test[0]
        buttons.append([InlineKeyboardButton(text=f"📝 Test #{test_code}", callback_data=f"view_test_{test_code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def test_management_keyboard(test_code: int):
    kb = [
        [
            InlineKeyboardButton(text="👥 Ishtirokchilar", callback_data=f"participants_{test_code}"),
            InlineKeyboardButton(text="🏁 Testni Yakunlash", callback_data=f"confirm_close_{test_code}")
        ],
        [InlineKeyboardButton(text="⬅️ Ro'yxatga Qaytish", callback_data="back_to_test_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def confirm_close_test_keyboard(test_code: int):
    kb = [
        [InlineKeyboardButton(text="✅ Ha, Yakunlansin", callback_data=f"close_test_{test_code}")],
        [InlineKeyboardButton(text="⬅️ Yo'q, Ortga", callback_data=f"view_test_{test_code}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
