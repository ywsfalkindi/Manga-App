from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from .services import pb_get_all, pb_get_one, get_telegram_link
from .models import Series, Chapter, ChapterPages

router = APIRouter()

@router.get("/series")
async def get_series(q: str = ""):
    filter_query = {"filter": f"title ~ '{q}'"} if q else {"sort": "-updated"}
    items = await pb_get_all("series", filter_query)
    # نحول file_id إلى رابط بروكسي خاص بنا
    for item in items:
        item['cover_url'] = f"/api/image/{item['cover_file_id']}"
    return items

@router.get("/chapters/{series_id}")
async def get_chapters(series_id: str):
    # ترتيب تنازلي للفصول
    chapters = await pb_get_all("chapters", {"filter": f"series_id='{series_id}'", "sort": "-chapter_number"})
    return chapters

@router.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str):
    # جلب الصفحات مرتبة
    pages_data = await pb_get_all("pages", {"filter": f"chapter_id='{chapter_id}'", "sort": "page_number"})
    
    if not pages_data:
        raise HTTPException(status_code=404, detail="Chapter not found")
        
    # منطق الفصل السابق والتالي
    current_chap = await pb_get_one("chapters", chapter_id)
    all_chaps = await pb_get_all("chapters", {
        "filter": f"series_id='{current_chap['series_id']}'", 
        "sort": "-chapter_number",
        "fields": "id,chapter_number"
    })
    
    curr_idx = next((i for i, c in enumerate(all_chaps) if c['id'] == chapter_id), -1)
    next_id = all_chaps[curr_idx - 1]['id'] if curr_idx > 0 else None
    prev_id = all_chaps[curr_idx + 1]['id'] if curr_idx < len(all_chaps) - 1 else None

    # إرجاع روابط الصور كـ Endpoints خاصة بنا
    image_urls = [f"/api/image/{p['file_id']}" for p in pages_data]
    
    return {
        "pages": image_urls,
        "next_chapter": next_id,
        "prev_chapter": prev_id,
        "chapter_number": current_chap['chapter_number']
    }

@router.get("/image/{file_id}")
async def proxy_image(file_id: str):
    """
    يقوم هذا الرابط بإعادة توجيه المستخدم للصورة الحقيقية.
    هذا يخفي توكن البوت ويجدد الروابط تلقائياً.
    """
    real_url = await get_telegram_link(file_id)
    if not real_url:
        return RedirectResponse("https://via.placeholder.com/400?text=Error")
    return RedirectResponse(real_url)