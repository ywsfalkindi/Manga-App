# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.concurrency import run_in_threadpool  # ⚡️ لجعل الكود المتزامن يعمل بكفاءة
from pocketbase import PocketBase
from pocketbase.utils import ClientResponseError
import httpx
import asyncio
import os
from dotenv import load_dotenv
from diskcache import Cache

# --- الإعدادات الأولية ---
load_dotenv()
app = FastAPI(
    title="MangaApp API",
    description="الواجهة الخلفية لتطبيق المانجا، مع تحسينات في الأمان والأداء.",
    version="2.0.0"
)

# --- Middlewares ---
# 🚀 تفعيل ضغط البيانات (يجعل التطبيق أسرع على الشبكات الضعيفة)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# تفعيل CORS للسماح بالوصول من أي مصدر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- الإعدادات العامة -----------------
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# التحقق من وجود المتغيرات الأساسية
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("❌ متغير TELEGRAM_BOT_TOKEN غير موجود في ملف .env")

pb = PocketBase(POCKETBASE_URL)

# ⚡️ عميل HTTP غير متزامن (لتحسين الأداء وإعادة استخدام الاتصالات)
async_httpx_client: httpx.AsyncClient | None = None

# ⚡ الكاش الذكي (يحفظ البيانات في مجلد محلي، فلا تضيع عند إعادة التشغيل)
cache = Cache("./cache_directory", size_limit=int(2e9)) # 2GB cache limit

# ----------------- دوال مساعدة -----------------

@app.on_event("startup")
async def startup_event():
    global async_httpx_client
    async_httpx_client = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_event():
    if async_httpx_client:
        await async_httpx_client.aclose()

async def fetch_telegram_path(file_id: str) -> str | None:
    """
    يجلب مسار الملف من تيليجرام مع نظام كاش قوي.
    """
    try:
        # 1. هل الرابط موجود في الكاش؟
        cached_path = await run_in_threadpool(cache.get, file_id)
        if cached_path:
            return cached_path

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        if async_httpx_client is None:
            raise RuntimeError("HTTPX client not initialized.")
        resp = await async_httpx_client.get(url, timeout=10.0)
        resp.raise_for_status() # يطلق خطأ إذا كانت الاستجابة غير ناجحة
        data = resp.json()
        
        if data.get('ok'):
            file_path = data['result']['file_path']
            # حفظ في الكاش لمدة 24 ساعة
            await run_in_threadpool(cache.set, file_id, file_path, expire=86400)
            return file_path
    except httpx.RequestError as e:
        print(f"❌ خطأ في الشبكة عند جلب مسار تيليجرام لـ {file_id}: {e}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع عند جلب مسار تيليجرام لـ {file_id}: {e}")
    return None

# ----------------- الروابط (API Endpoints) -----------------

@app.get("/series", summary="جلب كل سلاسل المانجا")
async def get_all_series():
    """
    يجلب قائمة بكل المانجا المتوفرة مع ترتيبها حسب آخر تحديث.
    """
    try:
        # ⚡️ تشغيل الكود المتزامن في thread-pool لتجنب حظر الخادم
        result_list = await run_in_threadpool(
            pb.collection('series').get_full_list, sort='-updated'
        )
        
        # ✨ تحويل البيانات بشكل آمن ونظيف
        data = [
            {
                "id": item.id,
                "title": item.title,
                "cover_url": item.cover_url,
                "created": item.created,
                "updated": item.updated
            }
            for item in result_list
        ]
        return data

    except ClientResponseError as e:
        print(f"❌ خطأ من PocketBase في /series: {e}")
        raise HTTPException(status_code=e.status, detail=f"PocketBase error: {e.data.get('message', str(e))}")
    except Exception as e:
        print(f"❌ خطأ فادح في /series: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred.")

@app.get("/chapters/{series_id}", summary="جلب فصول مانجا معينة")
async def get_chapters(series_id: str):
    """
    يجلب كل الفصول المتعلقة بمانجا معينة، مرتبة حسب رقم الفصل.
    """
    try:
        result_list = await run_in_threadpool(
            pb.collection('chapters').get_full_list,
            query_params={
                "filter": f'series_id="{series_id}"',
                "sort": "+chapter_number"
            }
        )
        # ✨ تحديد الحقول المطلوبة فقط
        return [
            {
                "id": item.id,
                "chapter_number": item.chapter_number,
                "title": item.title,
                "series_id": item.series_id,
                "created": item.created
            }
            for item in result_list
        ]
    except ClientResponseError as e:
        print(f"❌ خطأ من PocketBase في /chapters/{series_id}: {e}")
        raise HTTPException(status_code=e.status, detail=f"PocketBase error: {e.data.get('message', str(e))}")
    except Exception as e:
        print(f"❌ خطأ فادح في /chapters/{series_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred.")


@app.get("/pages/{chapter_id}", summary="جلب صفحات فصل معين")
async def get_pages(chapter_id: str):
    """
    يجلب روابط الصفحات لفصل معين. الروابط تشير إلى البروكسي الخاص بنا لحماية التوكن.
    """
    try:
        # 1. جلب بيانات الصفحات من قاعدة البيانات
        pages_records = await run_in_threadpool(
            pb.collection('pages').get_full_list,
            query_params={
                "filter": f'chapter_id="{chapter_id}"',
                "sort": "+page_number"
            }
        )
        
        # 2. تكوين روابط الصفحات لتمر عبر البروكسي الخاص بنا
        # 🔒 هذا يضمن عدم كشف أي معلومات حساسة للمستخدم
        image_urls = [f"/image-proxy/{page.file_id}" for page in pages_records]
            
        return {
            "pages": image_urls,
            "next_chapter": None, # يمكن تطويره لاحقاً
            "prev_chapter": None 
        }
    except ClientResponseError as e:
        print(f"❌ خطأ من PocketBase في /pages/{chapter_id}: {e}")
        raise HTTPException(status_code=e.status, detail=f"PocketBase error: {e.data.get('message', str(e))}")
    except Exception as e:
        print(f"❌ خطأ فادح في /pages/{chapter_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred.")


# 🔒 --- بروكسي الصور الآمن --- 🔒
@app.get("/image-proxy/{file_id}", summary="بروكسي آمن لجلب الصور من تيليجرام")
async def image_proxy(file_id: str):
    """
    يعمل كجسر آمن لجلب الصور. يخفي توكن البوت ويحمي الخادم.
    يستخدم StreamingResponse لنقل الصور بكفاءة دون استهلاك ذاكرة كبير.
    """
    if async_httpx_client is None:
        raise HTTPException(status_code=500, detail="HTTPX client not initialized.")

    # 1. جلب مسار الملف من تيليجرام (يستخدم الكاش)
    file_path = await fetch_telegram_path(file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Image not found on Telegram or failed to fetch path.")

    # 2. بناء رابط الصورة الفعلي
    image_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

    # 3. طلب الصورة بشكل تدفقي (Streaming)
    try:
        req = async_httpx_client.build_request("GET", image_url)
        r = await async_httpx_client.send(req, stream=True)
        r.raise_for_status()
        
        # 4. إرجاع الصورة للمستخدم بشكل تدفقي
        return StreamingResponse(r.aiter_bytes(), media_type=r.headers.get("content-type"))
    except httpx.HTTPStatusError as e:
        print(f"❌ خطأ في جلب الصورة {file_id} من تيليجرام: {e}")
        raise HTTPException(status_code=e.response.status_code, detail="Failed to proxy image from Telegram.")
    except Exception as e:
        print(f"❌ خطأ غير متوقع في البروكسي {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error in image proxy.")
