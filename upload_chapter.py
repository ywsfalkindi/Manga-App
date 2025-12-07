import os
import asyncio
import aiohttp
from pocketbase import PocketBase
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MY_CHAT_ID")
PB_URL = os.getenv("PB_URL", "http://127.0.0.1:8090")

if not TOKEN or not CHAT_ID:
    print("❌ خطأ: تأكد من إعداد ملف .env")
    exit()

pb = PocketBase(PB_URL)

async def upload_image_to_telegram(session, file_path, page_num):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    data = aiohttp.FormData()
    data.add_field('chat_id', CHAT_ID)
    data.add_field('photo', open(file_path, 'rb'))
    
    try:
        async with session.post(url, data=data, timeout=60) as resp:
            result = await resp.json()
            if result.get("ok"):
                file_id = result["result"]["photo"][-1]["file_id"]
                print(f"✅ تم رفع صفحة {page_num}")
                return {"page": page_num, "file_id": file_id}
            else:
                print(f"❌ فشل صفحة {page_num}: {result.get('description')}")
                return None
    except Exception as e:
        print(f"❌ خطأ اتصال صفحة {page_num}: {e}")
        return None

async def main_upload(folder_path, series_id, chapter_title, chapter_num):
    print(f"🚀 بدء رفع الفصل: {chapter_title}")
    
    try:
        chapter = pb.collection("chapters").create({
            "series_id": series_id,
            "title": chapter_title,
            "chapter_number": chapter_num
        })
        print(f"📘 تم إنشاء الفصل ID: {chapter.id}")
    except Exception as e:
        print(f"❌ خطأ في إنشاء الفصل (تأكد من Series ID): {e}")
        return

    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('jpg', 'jpeg', 'png', 'webp'))])
    if not files:
        print("⚠️ المجلد فارغ!")
        return

    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, filename in enumerate(files, 1):
            file_path = os.path.join(folder_path, filename)
            tasks.append(upload_image_to_telegram(session, file_path, idx))
        
        results = []
        # رفع 5 صور في كل دفعة لتجنب الحظر
        chunk_size = 5 
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i + chunk_size]
            results.extend(await asyncio.gather(*chunk))
            await asyncio.sleep(1) 

    success_count = 0
    for res in results:
        if res:
            try:
                pb.collection("pages").create({
                    "chapter_id": chapter.id,
                    "file_id": res["file_id"],
                    "page_number": res["page"]
                })
                success_count += 1
            except Exception as e:
                print(f"❌ خطأ حفظ في القاعدة: {e}")

    print(f"\n🎉 تم الانتهاء: {success_count}/{len(files)} صفحة.")

if __name__ == "__main__":
    # عدل هذه القيم
    SERIES_ID = "YOUR_SERIES_ID" 
    FOLDER = r"C:\Manga\OnePiece\Ch1000"
    CHAP_TITLE = "Chapter 1000"
    CHAP_NUM = 1000
    
    # asyncio.run(main_upload(FOLDER, SERIES_ID, CHAP_TITLE, CHAP_NUM))
    print("⚠️ قم بفك التعليق في أسفل الملف لتشغيل الرفع")