import os
import asyncio
import aiohttp
import orjson
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, Response
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# --- الإعدادات ---
PB_URL = os.getenv("PB_URL", "http://127.0.0.1:8090")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# تحديد عدد الطلبات المتزامنة لتجنب حظر تيليجرام
TG_SEMAPHORE = asyncio.Semaphore(20) 

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class ORJSONResponse(Response):
    media_type = "application/json"
    def render(self, content: any) -> bytes:
        return orjson.dumps(content)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # إعداد جلسة HTTP مع DNS caching واتصالات محسنة
    connector = aiohttp.TCPConnector(limit=500, ttl_dns_cache=300)
    app.state.http_session = aiohttp.ClientSession(connector=connector, json_serialize=orjson.dumps)
    print("🚀 Engine Started: Redis & HTTP Pool Ready with Semaphore protection")
    yield
    await app.state.http_session.close()
    await redis_client.close()
    print("💤 Engine Stopped")

app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- دوال المساعدة المتقدمة ---

async def get_cached_telegram_link(session: aiohttp.ClientSession, file_id: str):
    """
    جلب رابط الصورة مع الحماية من الحظر (Semaphore) والتخزين المؤقت.
    """
    if not file_id: return "https://via.placeholder.com/200x300?text=No+Image"
    
    cache_key = f"img:{file_id}"
    
    # 1. محاولة القراءة من الكاش
    try:
        cached_url = await redis_client.get(cache_key)
        if cached_url: return cached_url
    except Exception: pass

    # 2. الطلب من تيليجرام (محمي بالسيمافور)
    if not BOT_TOKEN:
        return "https://via.placeholder.com/600x800?text=No+Token"

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    
    async with TG_SEMAPHORE: # لا يسمح بمرور أكثر من 20 طلب في نفس اللحظة
        try:
            async with session.get(api_url) as resp:
                data = await resp.json()
                if data.get("ok"):
                    file_path = data["result"]["file_path"]
                    direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    
                    # تخزين الرابط لمدة 50 دقيقة (أقل من ساعة لضمان الأمان)
                    asyncio.create_task(redis_client.setex(cache_key, 3000, direct_url))
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
    جلب المانجا وتحويل cover_file_id إلى روابط حقيقية ديناميكياً
    """
    session = app.state.http_session
    # تقليل مدة الكاش هنا للتأكد من أن الروابط دائماً طازجة
    cache_key = f"api:series_v2:{q if q else 'all'}"
    
    cached = await redis_client.get(cache_key)
    if cached:
        return ORJSONResponse(content=orjson.loads(cached))

    params = {"sort": "-created", "fields": "id,title,cover_file_id"} # جلب file_id
    if q: params["filter"] = f"title ~ '{q}'"
    
    try:
        async with session.get(f"{PB_URL}/api/collections/series/records", params=params) as resp:
            data = await resp.json()
            items = data.get("items", [])
            
            # تحويل file_id إلى روابط حقيقية بشكل متوازي
            tasks = [get_cached_telegram_link(session, item.get("cover_file_id")) for item in items]
            cover_urls = await asyncio.gather(*tasks)
            
            # دمج النتائج
            result = []
            for item, url in zip(items, cover_urls):
                result.append({
                    "id": item["id"],
                    "title": item["title"],
                    "cover_url": url # إرسال الرابط الجاهز للواجهة
                })
            
            # كاش لمدة 5 دقائق للقائمة (الروابط داخلها صالحة لـ 50 دقيقة)
            await redis_client.setex(cache_key, 300, orjson.dumps(result))
            return result
            
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chapters/{series_id}")
async def get_chapters(series_id: str):
    session = app.state.http_session
    cache_key = f"api:chapters:{series_id}"
    
    cached = await redis_client.get(cache_key)
    if cached: return ORJSONResponse(content=orjson.loads(cached))

    params = {
        "filter": f'series_id="{series_id}"',
        "sort": "-chapter_number",
        "fields": "id,title,chapter_number"
    }

    try:
        async with session.get(f"{PB_URL}/api/collections/chapters/records", params=params) as resp:
            data = await resp.json()
            result = data.get("items", [])
            await redis_client.setex(cache_key, 30, orjson.dumps(result))
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str):
    session = app.state.http_session
    
    # 1. جلب معرفات الملفات (Cache DB response)
    db_cache_key = f"db:pages:{chapter_id}"
    cached_records = await redis_client.get(db_cache_key)
    
    if cached_records:
        records = orjson.loads(cached_records)
    else:
        params = {
            "filter": f'chapter_id="{chapter_id}"',
            "sort": "page_number",
            "fields": "file_id"
        }
        async with session.get(f"{PB_URL}/api/collections/pages/records", params=params) as resp:
            data = await resp.json()
            records = data.get("items", [])
            await redis_client.setex(db_cache_key, 3600, orjson.dumps(records))

    if not records: return {"pages": []}

    # 2. تحويل المعرفات إلى روابط (محمية بـ Semaphore داخل الدالة)
    tasks = [get_cached_telegram_link(session, r["file_id"]) for r in records]
    urls = await asyncio.gather(*tasks)
    
    return {"pages": urls}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)