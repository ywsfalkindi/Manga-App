# ================================================
# FILE: bot.py
# ================================================
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, PhotoSize
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

@dp.message(F.photo)
async def handle_photo(message: Message):
    photo: PhotoSize = message.photo[-1]
    file_id = photo.file_id
    
    # رسالة بسيطة لسهولة النسخ
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