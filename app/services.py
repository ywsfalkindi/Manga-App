# ================================================
# FILE: app/services.py
# ================================================
import httpx
from async_lru import alru_cache
from .config import settings

# متغير عالمي لتخزين العميل المشترك
shared_client: httpx.AsyncClient = None

def init_client():
    """تهيئة العميل عند بدء التشغيل"""
    global shared_client
    # connection pooling limits لمنع اختناق السيرفر
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
    shared_client = httpx.AsyncClient(timeout=10.0, limits=limits)
    print("✅ HTTP Client Initialized")

async def close_client():
    """إغلاق العميل عند إيقاف التشغيل"""
    global shared_client
    if shared_client:
        await shared_client.aclose()
        print("🛑 HTTP Client Closed")

# PocketBase Helper
async def pb_get_all(collection: str, query: dict = None):
    url = f"{settings.POCKETBASE_URL}/api/collections/{collection}/records"
    params = query or {}
    
    # === تحسين 1: إصلاح مشكلة اختفاء الفصول ===
    # PocketBase يرجع 30 عنصر افتراضياً. نرفع الحد إلى 500.
    if "perPage" not in params:
        params["perPage"] = 500
        
    try:
        # نستخدم العميل المشترك
        resp = await shared_client.get(url, params=params)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as e:
        print(f"PB Error ({collection}): {e}")
        return []

async def pb_get_one(collection: str, record_id: str):
    url = f"{settings.POCKETBASE_URL}/api/collections/{collection}/records/{record_id}"
    try:
        resp = await shared_client.get(url)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

# Telegram Service with Caching
@alru_cache(maxsize=1000, ttl=3000) # Cache link for 50 mins
async def get_telegram_link(file_id: str) -> str:
    """Gets a temporary direct link from Telegram and caches it."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    try:
        # استخدام العميل المشترك أيضاً
        resp = await shared_client.get(url)
        data = resp.json()
        if data.get("ok"):
            file_path = data["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
    except Exception as e:
        print(f"Telegram Error: {e}")
    return ""