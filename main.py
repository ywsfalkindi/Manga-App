from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pocketbase import PocketBase
import httpx # مكتبة أسرع تدعم التوازي
import asyncio # للمعالجة المتوازية
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- الإعدادات -----------------
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090") # قيمة افتراضية للأمان
pb = PocketBase(POCKETBASE_URL)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ⚡ ذاكرة مؤقتة بسيطة لتخزين مسارات الصور (Cache)
# المفتاح: file_id، القيمة: file_path
# هذا سيلغي الحاجة للاتصال بتيليجرام في المرات القادمة لنفس الصورة
files_cache = {}

# ----------------- دوال مساعدة -----------------

async def fetch_telegram_path(client, file_id):
    """
    يجلب مسار الملف من تيليجرام بشكل غير متزامن (سريع جداً)
    """
    # 1. التحقق من الكاش أولاً
    if file_id in files_cache:
        return files_cache[file_id]

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        resp = await client.get(url)
        data = resp.json()
        
        if data.get('ok'):
            file_path = data['result']['file_path']
            # حفظ في الكاش للمستقبل
            files_cache[file_id] = file_path
            return file_path
    except Exception as e:
        print(f"Error fetching {file_id}: {e}")
    return None

# ----------------- الروابط (APIs) -----------------

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.get("/series")
def get_all_series():
    # PocketBase سريع محلياً، لا يحتاج لتعديل كبير هنا
    result = pb.collection('series').get_full_list()
    return [item.__dict__ for item in result]

@app.get("/chapters/{series_id}")
def get_chapters(series_id: str):
    result = pb.collection('chapters').get_full_list(
        query_params={
            "filter": f'series_id="{series_id}"',
            "sort": "+chapter_number"
        }
    )
    return [item.__dict__ for item in result]

# 🔥 التعديل الجوهري هنا 🔥
@app.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str): # لاحظ استخدام async
    # 1. جلب البيانات من قاعدة البيانات (سريع)
    result = pb.collection('pages').get_full_list(
        query_params={
            "filter": f'chapter_id="{chapter_id}"',
            "sort": "+page_number"
        }
    )
    
    # 2. تجهيز قائمة المهام (Tasks) لإرسالها دفعة واحدة
    async with httpx.AsyncClient() as client:
        tasks = []
        for page in result:
            # نضيف المهمة للقائمة بدلاً من انتظارها
            tasks.append(fetch_telegram_path(client, page.file_id))
        
        # 3. إطلاق الصواريخ! (تنفيذ كل الطلبات في نفس اللحظة)
        paths = await asyncio.gather(*tasks)

    # 4. تكوين الروابط النهائية
    image_urls = []
    for path in paths:
        if path:
            final_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{path}"
            image_urls.append(final_url)
            
    return {"pages": image_urls}