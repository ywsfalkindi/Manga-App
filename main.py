# main.py
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware  # 🚀 ضغط البيانات لتسريع التطبيق
from pocketbase import PocketBase
import httpx
import asyncio
import os
from dotenv import load_dotenv
from diskcache import Cache  # 🚀 كاش دائم على القرص

load_dotenv()
app = FastAPI()

# تفعيل ضغط البيانات (يجعل التطبيق أسرع على الشبكات الضعيفة)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- الإعدادات -----------------
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")
pb = PocketBase(POCKETBASE_URL)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ⚡ الكاش الذكي (يحفظ البيانات في مجلد محلي، فلا تضيع عند إعادة التشغيل)
cache = Cache("./cache_directory")

# ----------------- دوال مساعدة -----------------

async def fetch_telegram_path(client, file_id):
    """
    يجلب مسار الملف من تيليجرام مع نظام كاش قوي
    """
    # 1. هل الرابط موجود في الكاش؟
    cached_path = cache.get(file_id)
    if cached_path:
        return cached_path

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        resp = await client.get(url, timeout=5.0) # إضافة timeout لتجنب التعليق
        data = resp.json()
        
        if data.get('ok'):
            file_path = data['result']['file_path']
            # حفظ في الكاش لمدة 24 ساعة (أو أكثر)
            cache.set(file_id, file_path, expire=86400) 
            return file_path
    except Exception as e:
        print(f"Error fetching {file_id}: {e}")
    return None

# ----------------- الروابط (APIs) -----------------

@app.get("/")
def read_root():
    return FileResponse("index.html")

# ملف المانيفست لتثبيت التطبيق
@app.get("/manifest.json")
def get_manifest():
    return FileResponse("manifest.json")

@app.get("/series")
def get_all_series():
    try:
        print("🔄 جاري الاتصال بـ PocketBase...")
        # جلب البيانات
        result = pb.collection('series').get_full_list(sort='-updated')
        print(f"✅ تم جلب {len(result)} مانجا.")
        
        # تحويل البيانات بشكل آمن
        data = []
        for item in result:
            data.append({
                "id": item.id,
                "title": item.title,
                "cover_url": item.cover_url,
                "created": item.created,
                "updated": item.updated
            })
        return data

    except Exception as e:
        # طباعة الخطأ في التيرمنال لنعرف السبب
        print(f"❌ خطأ فادح في /series: {str(e)}")
        # إرجاع الخطأ للمتصفح أيضاً
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/chapters/{series_id}")
def get_chapters(series_id: str):
    try:
        result = pb.collection('chapters').get_full_list(
            query_params={
                "filter": f'series_id="{series_id}"',
                "sort": "+chapter_number" # ترتيب تصاعدي
            }
        )
        return [item.__dict__ for item in result]
    except:
        return []

@app.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str):
    try:
        # 1. جلب الصفحات
        result = pb.collection('pages').get_full_list(
            query_params={
                "filter": f'chapter_id="{chapter_id}"',
                "sort": "+page_number"
            }
        )
        
        # 2. المعالجة المتوازية
        async with httpx.AsyncClient() as client:
            tasks = [fetch_telegram_path(client, page.file_id) for page in result]
            paths = await asyncio.gather(*tasks)

        # 3. تكوين الروابط
        image_urls = []
        for path in paths:
            if path:
                image_urls.append(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{path}")
            
        return {
            "pages": image_urls,
            "next_chapter": None, # يمكن تطويره لاحقاً من الباك إند، لكن سنعالجه في الفرونت إند حالياً
            "prev_chapter": None 
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})