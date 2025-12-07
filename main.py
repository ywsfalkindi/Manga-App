from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.concurrency import run_in_threadpool
from pocketbase import PocketBase
from contextlib import asynccontextmanager
import os
import time
import aiohttp
import asyncio
from dotenv import load_dotenv

# تحميل المتغيرات
load_dotenv()

# إعدادات الاتصال والأمان
PB_URL = os.getenv("PB_URL", "http://127.0.0.1:8090")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# الاتصال بقاعدة البيانات (Synchronous)
pb = PocketBase(PB_URL)

# --- نظام الكاش في الذاكرة ---
# تخزين: {file_id: {'url': str, 'expires_at': float}}
link_cache = {}

# --- إدارة دورة حياة التطبيق (Lifespan) ---
# لإنشاء جلسة اتصال واحدة وإعادة استخدامها (أسرع بكثير)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # بدء الجلسة عند التشغيل
    app.state.http_session = aiohttp.ClientSession()
    print("🚀 System started & HTTP Client ready.")
    yield
    # إغلاق الجلسة عند الإيقاف
    await app.state.http_session.close()
    print("💤 System shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- دوال المساعدة (Helpers) ---

async def get_telegram_link_async(session: aiohttp.ClientSession, file_id: str):
    """جلب رابط مباشر بسرعة فائقة مع الكاش"""
    current_time = time.time()
    
    # 1. فحص الكاش
    if file_id in link_cache:
        data = link_cache[file_id]
        if current_time < data["expires_at"]:
            return data["url"]

    # 2. طلب جديد (غير متزامن)
    try:
        if not BOT_TOKEN:
            return "https://placehold.co/600x800?text=No+Token"
            
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        async with session.get(url, timeout=5) as resp:
            res_json = await resp.json()
            
            if res_json.get("ok"):
                file_path = res_json["result"]["file_path"]
                direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                
                # حفظ في الكاش لمدة 55 دقيقة (روابط تيليجرام تنتهي خلال ساعة)
                link_cache[file_id] = {
                    "url": direct_url,
                    "expires_at": current_time + (55 * 60)
                }
                return direct_url
    except Exception as e:
        print(f"⚠️ Error fetching TG link for {file_id}: {e}")
    
    # صورة احتياطية في حال الفشل
    return "https://placehold.co/600x800?text=Error+Loading"

# --- الـ Endpoints ---

@app.get("/")
async def read_root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: index.html not found</h1>", status_code=404)

@app.get("/series")
async def get_series():
    try:
        # تشغيل طلب قاعدة البيانات في Thread منفصل لعدم تعطيل السيرفر
        records = await run_in_threadpool(
            lambda: pb.collection("series").get_full_list(query_params={"sort": "-created"})
        )
        return [{"id": r.id, "title": r.title, "cover_url": r.cover_url} for r in records]
    except Exception as e:
        print(f"❌ Error in /series: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chapters/{series_id}")
async def get_chapters(series_id: str):
    try:
        records = await run_in_threadpool(
            lambda: pb.collection("chapters").get_full_list(
                query_params={"filter": f'series_id="{series_id}"', "sort": "-chapter_number"}
            )
        )
        return [{"id": r.id, "title": r.title, "chapter_number": r.chapter_number} for r in records]
    except Exception as e:
        print(f"❌ Error in /chapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str):
    try:
        # 1. جلب معرفات الملفات من قاعدة البيانات
        records = await run_in_threadpool(
            lambda: pb.collection("pages").get_full_list(
                query_params={"filter": f'chapter_id="{chapter_id}"', "sort": "page_number"}
            )
        )
        
        # 2. تحضير المهام (Tasks) للتنفيذ المتوازي
        session = app.state.http_session
        tasks = [get_telegram_link_async(session, r.file_id) for r in records]
        
        # 3. تنفيذ جميع الطلبات في نفس اللحظة (Parallel Execution)
        # هذا هو سر السرعة: ننتظر أطول طلب فقط، وليس مجموع الطلبات
        urls = await asyncio.gather(*tasks)
        
        return {"pages": urls}
    except Exception as e:
        print(f"❌ Error in /pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))