from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pocketbase import PocketBase
import os
import requests
import time
from dotenv import load_dotenv

# تحميل المتغيرات
load_dotenv()

app = FastAPI()

# إعدادات الأمان (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# الاتصال بقاعدة البيانات
PB_URL = os.getenv("PB_URL", "http://127.0.0.1:8090")
pb = PocketBase(PB_URL)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- نظام الكاش (Cache) لتسريع الصور ---
link_cache = {}

def get_telegram_link(file_id):
    """تحويل File ID إلى رابط مباشر مع التخزين المؤقت"""
    current_time = time.time()
    
    # 1. هل الرابط موجود في الكاش وصالح؟
    if file_id in link_cache:
        data = link_cache[file_id]
        if current_time < data["expires_at"]:
            return data["url"]
    
    # 2. طلب رابط جديد من تيليجرام
    try:
        if not BOT_TOKEN:
            return None
            
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=5)
        res_json = res.json()
        
        if res_json.get("ok"):
            file_path = res_json["result"]["file_path"]
            direct_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            
            # حفظ في الكاش لمدة 50 دقيقة
            link_cache[file_id] = {
                "url": direct_url,
                "expires_at": current_time + (50 * 60)
            }
            return direct_url
    except Exception as e:
        print(f"⚠️ Error fetching TG link: {e}")
    
    return None

# --- الـ Endpoints ---

@app.get("/")
def read_root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: index.html not found</h1>", status_code=404)

@app.get("/series")
def get_series():
    try:
        # ✅ تم التصحيح هنا: استخدام query_params بدلاً من sort مباشرة
        records = pb.collection("series").get_full_list(
            query_params={"sort": "-created"}
        )
        data = [{"id": r.id, "title": r.title, "cover_url": r.cover_url} for r in records]
        return data
    except Exception as e:
        print(f"❌ Error in /series: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chapters/{series_id}")
def get_chapters(series_id: str):
    try:
        # ✅ هذه كانت صحيحة، أبقيناها كما هي
        records = pb.collection("chapters").get_full_list(
            query_params={"filter": f'series_id="{series_id}"', "sort": "-chapter_number"}
        )
        data = [{"id": r.id, "title": r.title, "chapter_number": r.chapter_number} for r in records]
        return data
    except Exception as e:
        print(f"❌ Error in /chapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pages/{chapter_id}")
def get_pages(chapter_id: str):
    try:
        # جلب الصفحات
        records = pb.collection("pages").get_full_list(
            query_params={"filter": f'chapter_id="{chapter_id}"', "sort": "page_number"}
        )
        
        # تحويل file_id إلى روابط حقيقية
        urls = []
        for r in records:
            url = get_telegram_link(r.file_id)
            if url:
                urls.append(url)
            else:
                # صورة احتياطية في حال الفشل
                urls.append("https://placehold.co/600x800?text=Error+Loading+Image")
        
        return {"pages": urls}
    except Exception as e:
        print(f"❌ Error in /pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))