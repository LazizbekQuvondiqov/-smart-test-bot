# database.py
import aiosqlite
import logging
from config import DB_NAME
import time

async def setup_database():
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("ALTER TABLE tests ADD COLUMN status TEXT DEFAULT 'active'")
            await db.execute("ALTER TABLE tests ADD COLUMN question_file_type TEXT")
            await db.execute("ALTER TABLE channels ADD COLUMN username TEXT")
            await db.execute("ALTER TABLE channels ADD COLUMN invite_link TEXT")
            await db.commit()
        except aiosqlite.OperationalError:
            pass

        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, referred_by_id INTEGER, referral_count INTEGER DEFAULT 0, status TEXT DEFAULT 'active')''')
        await db.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id INTEGER PRIMARY KEY, username TEXT, invite_link TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS tests (id INTEGER PRIMARY KEY AUTOINCREMENT, test_code INTEGER UNIQUE, owner_user_id INTEGER, question_file_id TEXT, question_file_type TEXT, answer_key TEXT, duration_minutes INTEGER, created_at INTEGER NOT NULL, status TEXT DEFAULT 'active')''')
        await db.execute('''CREATE TABLE IF NOT EXISTS user_test_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, test_id INTEGER, start_time INTEGER, FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE, UNIQUE(user_id, test_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS user_answers (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, user_id INTEGER, score INTEGER, submitted_answers TEXT, submitted_at INTEGER, FOREIGN KEY (session_id) REFERENCES user_test_sessions (id) ON DELETE CASCADE, UNIQUE(session_id, user_id))''')
        await db.commit()
        logging.info("Ma'lumotlar bazasi muvaffaqiyatli sozlandi.")

async def add_user(user_id, username, full_name, referred_by_id=None) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_exists = await cursor.fetchone()

        if not user_exists:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, referred_by_id) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, referred_by_id)
            )
            await db.commit()
            return True
        else:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ?, status = 'active' WHERE user_id = ?",
                (username, full_name, user_id)
            )
            await db.commit()
            return False

async def add_channel(channel_id, username=None, invite_link=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT channel_id FROM channels WHERE channel_id = ?", (channel_id,))
        if await cursor.fetchone():
            await db.execute("UPDATE channels SET username = ?, invite_link = ? WHERE channel_id = ?", (username, invite_link, channel_id))
            await db.commit()
            return False
        else:
            await db.execute("INSERT INTO channels (channel_id, username, invite_link) VALUES (?, ?, ?)", (channel_id, username, invite_link))
            await db.commit()
            return True

async def get_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT channel_id, username, invite_link FROM channels")
        return await cursor.fetchall()

async def update_referral_count(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_referred_by(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT referred_by_id FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def create_test(owner_user_id, question_file_id, question_file_type, answer_key, duration_minutes):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT MAX(test_code) FROM tests")
        last_code_result = await cursor.fetchone()
        last_code = last_code_result[0] if last_code_result[0] else 1000
        new_code = 1001 if last_code < 1001 else last_code + 1
        await db.execute(
            "INSERT INTO tests (test_code, owner_user_id, question_file_id, question_file_type, answer_key, duration_minutes, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_code, owner_user_id, question_file_id, question_file_type, answer_key, duration_minutes, int(time.time()), 'active')
        )
        await db.commit()
        return new_code

async def get_test_by_code(test_code):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, question_file_id, question_file_type, duration_minutes, owner_user_id, answer_key, status FROM tests WHERE test_code = ?",
            (test_code,)
        )
        return await cursor.fetchone()

async def get_user_fullname(user_id):
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,)); result = await cursor.fetchone(); return result[0] if result else None

async def get_user_referral_count(user_id):
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,)); result = await cursor.fetchone(); return result[0] if result else 0

async def get_contest_stats():
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT full_name, referral_count FROM users WHERE referral_count > 0 ORDER BY referral_count DESC LIMIT 10"); return await cursor.fetchall()

async def clear_all_referral_counts():
    async with aiosqlite.connect(DB_NAME) as db: await db.execute("UPDATE users SET referral_count = 0"); await db.commit()

async def get_all_user_ids():
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT user_id FROM users WHERE status = 'active'"); return [row[0] for row in await cursor.fetchall()]

async def get_active_users_count():
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT COUNT(user_id) FROM users WHERE status = 'active'"); result = await cursor.fetchone(); return result[0] if result else 0

async def delete_channel(channel_id):
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,)); await db.commit(); return cursor.rowcount > 0

async def close_test(test_code: int):
    async with aiosqlite.connect(DB_NAME) as db: await db.execute("UPDATE tests SET status = 'closed' WHERE test_code = ?", (test_code,)); await db.commit()

async def start_user_session(user_id, test_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("INSERT INTO user_test_sessions (user_id, test_id, start_time) VALUES (?, ?, ?)", (user_id, test_id, int(time.time())))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_user_session(user_id, test_id):
     async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT id, start_time FROM user_test_sessions WHERE user_id = ? AND test_id = ?", (user_id, test_id)); return await cursor.fetchone()

async def save_user_answer(session_id, user_id, score, submitted_answers):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("INSERT INTO user_answers (session_id, user_id, score, submitted_answers, submitted_at) VALUES (?, ?, ?, ?, ?)", (session_id, user_id, score, submitted_answers, int(time.time())))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_user_tests(owner_user_id):
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT test_code FROM tests WHERE owner_user_id = ? AND status = 'active' ORDER BY id DESC", (owner_user_id,)); return await cursor.fetchall()

async def get_test_participant_count(test_code: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT COUNT(ua.id) FROM user_answers ua JOIN user_test_sessions uts ON ua.session_id = uts.id JOIN tests t ON uts.test_id = t.id WHERE t.test_code = ?", (test_code,)); result = await cursor.fetchone(); return result[0] if result else 0

# --- O'ZGARISH: `get_test_results` funksiyasi to'liq yangilandi ---
async def get_test_results(test_code):
    """
    Excel uchun barcha kerakli ma'lumotlarni oladi:
    F.I.O, ID, ball, boshlash vaqti, tugatish vaqti.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, owner_user_id, answer_key FROM tests WHERE test_code = ?", (test_code,))
        test_info = await cursor.fetchone()
        if not test_info:
            return None, None, None

        test_id, owner_user_id, answer_key = test_info

        # SQL so'roviga `uts.start_time` va `ua.submitted_at` qo'shildi
        query = """
        SELECT
            u.user_id,
            u.full_name,
            ua.score,
            uts.start_time,
            ua.submitted_at
        FROM
            user_answers ua
        JOIN
            user_test_sessions uts ON ua.session_id = uts.id
        JOIN
            users u ON ua.user_id = u.user_id
        WHERE
            uts.test_id = ?
        ORDER BY
            ua.score DESC,
            (ua.submitted_at - uts.start_time) ASC
        """
        # ORDER BY: avval balli yuqorilar, keyin tezroq ishlaganlar
        cursor = await db.execute(query, (test_id,))
        results = await cursor.fetchall()

        return results, owner_user_id, answer_key

async def get_user_answer_details(test_code, user_id):
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT t.answer_key, ua.submitted_answers FROM tests t JOIN user_test_sessions uts ON t.id = uts.test_id JOIN user_answers ua ON uts.id = ua.session_id WHERE t.test_code = ? AND uts.user_id = ?", (test_code, user_id)); return await cursor.fetchone()

async def has_user_answered(user_id, test_id):
    async with aiosqlite.connect(DB_NAME) as db: cursor = await db.execute("SELECT ua.id FROM user_answers ua JOIN user_test_sessions uts ON ua.session_id = uts.id WHERE uts.user_id = ? AND uts.test_id = ?", (user_id, test_id)); return await cursor.fetchone() is not None

async def delete_old_tests(days_old: int = 4):
    async with aiosqlite.connect(DB_NAME) as db:
        time_threshold = int(time.time()) - (days_old * 24 * 60 * 60)
        cursor = await db.execute("DELETE FROM tests WHERE created_at < ? AND status = 'closed'", (time_threshold,))
        deleted_count = cursor.rowcount
        await db.commit()
        if deleted_count > 0:
            logging.info(f"{deleted_count} ta eskirgan va yopilgan test bazadan o'chirildi.")
        return deleted_count
