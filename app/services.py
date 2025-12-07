import httpx
from async_lru import alru_cache
from .config import settings

# PocketBase Helper
async def pb_get_all(collection: str, query: dict = None):
    url = f"{settings.POCKETBASE_URL}/api/collections/{collection}/records"
    params = query or {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            print(f"PB Error: {e}")
            return []

async def pb_get_one(collection: str, record_id: str):
    url = f"{settings.POCKETBASE_URL}/api/collections/{collection}/records/{record_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except:
            return None

# Telegram Service with Caching
@alru_cache(maxsize=1000, ttl=3000) # Cache link for 50 mins
async def get_telegram_link(file_id: str) -> str:
    """Gets a temporary direct link from Telegram and caches it."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=3.0)
            data = resp.json()
            if data.get("ok"):
                file_path = data["result"]["file_path"]
                return f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
        except Exception as e:
            print(f"Telegram Error: {e}")
    return ""