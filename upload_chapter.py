import os
import asyncio
import aiohttp
from pocketbase import PocketBase
from dotenv import load_dotenv

# تحميل الإعدادات
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MY_CHAT_ID")
PB_URL = os.getenv("PB_URL")

if not TOKEN or not CHAT_ID:
    print("❌ خطأ: تأكد من إعداد ملف .env")
    exit()

pb = PocketBase(PB_URL)

async def upload_image_to_telegram(session, file_path, page_num):
    """رفع صورة واحدة لتيليجرام"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    data = aiohttp.FormData()
    data.add_field('chat_id', CHAT_ID)
    data.add_field('photo', open(file_path, 'rb'))
    
    try:
        async with session.post(url, data=data) as resp:
            result = await resp.json()
            if result.get("ok"):
                # نأخذ أكبر حجم للصورة
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
    
    # 1. إنشاء سجل الفصل في قاعدة البيانات
    try:
        chapter_data = {
            "series_id": series_id,
            "title": chapter_title,
            "chapter_number": chapter_num
        }
        chapter = pb.collection("chapters").create(chapter_data)
        print(f"📘 تم إنشاء الفصل ID: {chapter.id}")
    except Exception as e:
        print(f"❌ خطأ في إنشاء الفصل في PocketBase: {e}")
        return

    # 2. تجهيز الصور
    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('jpg', 'jpeg', 'png', 'webp'))])
    if not files:
        print("⚠️ المجلد فارغ!")
        return

    # 3. الرفع المتوازي (الأسرع)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, filename in enumerate(files, 1):
            file_path = os.path.join(folder_path, filename)
            tasks.append(upload_image_to_telegram(session, file_path, idx))
        
        print(f"⏳ جاري رفع {len(files)} صورة معاً...")
        results = await asyncio.gather(*tasks)

    # 4. حفظ النتائج الناجحة في قاعدة البيانات
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
                print(f"❌ فشل حفظ صفحة {res['page']} في القاعدة: {e}")

    print(f"\n🎉 تم الانتهاء! تم رفع {success_count}/{len(files)} صفحة بنجاح.")

# --- التشغيل ---
if __name__ == "__main__":
    # مثال للاستخدام:
    # 1. احصل على ID السلسلة من PocketBase Admin UI
    # 2. ضع مسار المجلد هنا
    
    SERIES_ID = "YOUR_SERIES_ID_HERE" # 🔴 استبدل هذا بآيدي السلسلة من الموقع
    FOLDER = r"C:\Users\MTC Admin\Desktop\Manga_Chapter"
    
    # لتشغيل السكربت، أزل التعليق عن السطر التالي:
    # asyncio.run(main_upload(FOLDER, SERIES_ID, "الفصل الأول", 1))
    print("🔴 قم بتعديل السطور الأخيرة في الملف لتشغيل الرفع")