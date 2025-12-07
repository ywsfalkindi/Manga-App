# ================================================
# FILE: bot.py
# ================================================
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, PhotoSize, Document
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    exit("Error: NO TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🤖 أهلاً بك! أرسل لي صورة المانجا وسأقوم باستخراج المعرف (File ID).")

# === تحسين 6: دعم الصور العادية والملفات ===
@dp.message(F.photo | F.document)
async def handle_files(message: Message):
    file_id = None
    
    if message.photo:
        # الصورة تأتي بعدة أحجام، نأخذ الأكبر
        file_id = message.photo[-1].file_id
    elif message.document:
        # إذا كانت مستند/ملف
        if "image" in (message.document.mime_type or ""):
            file_id = message.document.file_id
        else:
            await message.reply("⚠️ هذا الملف ليس صورة.")
            return

    if file_id:
        response_text = (
            f"🆔 معرف الصورة:\n"
            f"<code>{file_id}</code>"
        )
        await message.reply(response_text, parse_mode="HTML")
        print(f"✅ Extracted: {file_id[:10]}...")

async def main():
    print("🚀 Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")