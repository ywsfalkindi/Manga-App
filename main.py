from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pocketbase import PocketBase
import requests
import os
from dotenv import load_dotenv # <--- استيراد جديد

load_dotenv()
app = FastAPI()

# إعدادات الأمان (CORS) للسماح بالوصول من أي مكان
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- الإعدادات -----------------
# الاتصال بسيرفر PocketBase المحلي
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
pb = PocketBase(POCKETBASE_URL)

# توكن البوت الخاص بك (تأكد أنه صحيح)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ----------------- الروابط (APIs) -----------------

# 1. الصفحة الرئيسية (لإرسال ملف الواجهة للجوال)
@app.get("/")
def read_root():
    return FileResponse("index.html")

# 2. جلب قائمة المانجات (السلاسل)
@app.get("/series")
def get_all_series():
    # يجلب كل المانجات المضافة في جدول series
    result = pb.collection('series').get_full_list()
    return [item.__dict__ for item in result]

# 3. جلب فصول مانجا محددة
@app.get("/chapters/{series_id}")
def get_chapters(series_id: str):
    # يجلب الفصول الخاصة بالسلسلة المطلوبة فقط، مرتبة تصاعدياً
    result = pb.collection('chapters').get_full_list(
        query_params={
            "filter": f'series_id="{series_id}"',
            "sort": "+chapter_number"
        }
    )
    return [item.__dict__ for item in result]

# 4. جلب صور الفصل (للقراءة)
@app.get("/pages/{chapter_id}")
def get_pages(chapter_id: str):
    # يجلب الصفحات الخاصة بالفصل، مرتبة حسب رقم الصفحة
    result = pb.collection('pages').get_full_list(
        query_params={
            "filter": f'chapter_id="{chapter_id}"',
            "sort": "+page_number"
        }
    )
    
    image_urls = []
    for page in result:
        file_id = page.file_id
        try:
            # نطلب من تيليجرام تحويل الـ File ID إلى مسار يمكن تحميله
            api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
            path_resp = requests.get(api_url).json()
            
            if path_resp.get('ok'):
                file_path = path_resp['result']['file_path']
                # تكوين الرابط النهائي للصورة
                final_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                image_urls.append(final_url)
        except Exception as e:
            print(f"Error getting image: {e}")
            continue
            
    return {"pages": image_urls}