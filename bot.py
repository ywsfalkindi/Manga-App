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
    await message.answer("🤖 أهلاً بك! أرسل لي صورة المانجا (أو عدة صور) وسأقوم بإعطائك معرف الملف (File ID) لاستخدامه في قاعدة البيانات.")

@dp.message(F.photo)
async def handle_photo(message: Message):
    # الحصول على أكبر حجم للصورة
    photo: PhotoSize = message.photo[-1]
    file_id = photo.file_id
    
    response_text = (
        f"📸 <b>تم استلام صورة!</b>\n"
        f"🆔 <code>{file_id}</code>\n"
        f"📋 اضغط على المعرف لنسخه."
    )
    await message.reply(response_text, parse_mode="HTML")
    print(f"✅ New Image: {file_id}")

async def main():
    print("🚀 Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")