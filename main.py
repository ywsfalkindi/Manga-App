import os
import time
import json
import asyncio
import aiohttp
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# --- الإعدادات ---
PB_URL = os.getenv("PB_URL", "http://127.0.0.1:8090")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# الاتصال بـ Redis
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # إعداد جلسة HTTP واحدة فائقة السرعة مع Connection Pooling
    connector = aiohttp.TCPConnector(limit=500, ttl_dns_cache=300)
    app.state.http_session = aiohttp.ClientSession(connector=connector)
    print("🚀 Engine Started: Redis & HTTP Pool Ready")
    yield
    # تنظيف عند الإغلاق
    await app.state.http_session.close()
    await redis_client.close()
    print("💤 Engine Stopped")

app = FastAPI(lifespan=lifespan)

# تفعيل ضغط البيانات لتسريع النقل
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- دوال المساعدة المتقدمة (Async + Cache) ---

async def get_cached_telegram_link(session: aiohttp.ClientSession, file_id: str):
    """
    جلب رابط الصورة.
    1. البحث في Redis (سرعة ميكرو ثانية).
    2. إذا لم يوجد، طلبه من تيليجرام وحفظه في Redis.
    """
    cache_key = f"img:{file_id}"
    
    # 1. محاولة القراءة من الكاش
    try:
        cached_url = await redis_client.get(cache_key)
        if cached_url:
            return cached_url
    except Exception:
        pass # تجاهل أخطاء Redis واستمر

    # 2. الطلب من تيليجرام في حال عدم وجوده في الكاش
    if not BOT_TOKEN:
        return "https://via.placeholder.com/600x800?text=No+Token"

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    try:
        async with session.get(api_url) as resp:
            data = await resp.json()
            if data.get("ok"):
                file_path = data["result"]["file_path"]
                direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                
                # حفظ في Redis لمدة 55 دقيقة (روابط تيليجرام تنتهي بعد ساعة)
                # استخدام Fire-and-forget للحفظ لعدم تعطيل الرد
                asyncio.create_task(redis_client.setex(cache_key, 3300, direct_url))
                
                return direct_url
    except Exception as e:
        print(f"⚠️ Error fetching TG link: {e}")
    
    return "https://via.placeholder.com/600x800?text=Error"

# --- Endpoints ---

@app.get("/")
async def read_root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)

@app.get("/series")
async def get_series(q: str = Query(None, min_length=1)):
    """
    جلب المانجا مع دعم البحث وتخزين النتائج مؤقتاً
    """
    session = app.state.http_session
    cache_key = f"api:series:{q if q else 'all'}"
    
    # فحص الكاش للنتائج
    cached = await redis_client.get(cache_key)
    if cached:
        return JSONResponse(content=json.loads(cached))

    # بناء الاستعلام لـ PocketBase
    params = {
        "sort": "-created",
        "fields": "id,title,cover_url"
    }
    if q:
        params["filter"] = f"title ~ '{q}'"
    
    try:
        async with session.get(f"{PB_URL}/api/collections/series/records", params=params) as resp:
            data = await resp.json()
            items = data.get("items", [])
            
            result = [{"id": r["id"], "title": r["title"], "cover_url": r["cover_url"]} for r in items]
            
            # حفظ نتيجة البحث لمدة دقيقة واحدة لتخفيف الحمل
            await redis_client.setex(cache_key, 60, json.dumps(result))
            
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chapters/{series_id}")
async def get_chapters(series_id: str):
    session = app.state.http_session
    # كاش قائمة الفصول لمدة 30 ثانية فقط لأنها قد تتحدث
    cache_key = f"api:chapters:{series_id}"
    
    cached = await redis_client.get(cache_key)
    if cached:
        return JSONResponse(content=json.loads(cached))

    params = {
        "filter": f'series_id="{series_id}"',
        "sort": "-chapter_number",
        "fields": "id,title,chapter_number"
    }

    try:
        async with session.get(f"{PB_URL}/api/collections/chapters/records", params=params) as resp:
            data = await resp.json()
            items = data.get("items", [])
            
            result = [{"id": r["id"], "title": r["title"], "chapter_number": r["chapter_number"]} for r in items]
            
            await redis_client.setex(cache_key, 30, json.dumps(result))
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str):
    session = app.state.http_session
    
    # 1. جلب معرفات الملفات من قاعدة البيانات
    # نستخدم الكاش هنا أيضاً لتقليل طلبات قاعدة البيانات
    db_cache_key = f"db:pages:{chapter_id}"
    cached_records = await redis_client.get(db_cache_key)
    
    if cached_records:
        records = json.loads(cached_records)
    else:
        params = {
            "filter": f'chapter_id="{chapter_id}"',
            "sort": "page_number",
            "fields": "file_id"
        }
        async with session.get(f"{PB_URL}/api/collections/pages/records", params=params) as resp:
            data = await resp.json()
            records = data.get("items", [])
            # حفظ هيكل الفصل في الكاش لفترة طويلة (مثلاً ساعة)
            await redis_client.setex(db_cache_key, 3600, json.dumps(records))

    if not records:
        return {"pages": []}

    # 2. تحويل معرفات الملفات إلى روابط مباشرة (بشكل متوازي صاروخي)
    # استخدام gather لتشغيل جميع الطلبات في نفس اللحظة
    tasks = [get_cached_telegram_link(session, r["file_id"]) for r in records]
    urls = await asyncio.gather(*tasks)
    
    return {"pages": urls}

# تشغيل السيرفر (للتطوير فقط، في الإنتاج استخدم الأمر في الأسفل)
if __name__ == "__main__":
    import uvicorn
    # استخدام uvloop لزيادة الأداء
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)