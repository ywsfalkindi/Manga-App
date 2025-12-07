# ================================================
# FILE: app/api.py
# ================================================
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from .services import pb_get_all, pb_get_one, get_telegram_link
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/series")
async def get_series(q: str = ""):
    try:
        filter_query = {"filter": f"title ~ '{q}'"} if q else {"sort": "-updated"}
        items = await pb_get_all("series", filter_query)
        
        cleaned_items = []
        for item in items:
            cover_id = item.get('cover_file_id') 
            if cover_id:
                item['cover_url'] = f"/api/image/{cover_id}"
            else:
                item['cover_url'] = "https://via.placeholder.com/300x450?text=No+Cover"
            cleaned_items.append(item)
            
        return cleaned_items
    except Exception as e:
        logger.error(f"Error in get_series: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chapters/{series_id}")
async def get_chapters(series_id: str):
    try:
        # جلب الفصول مرتبة تنازلياً
        chapters = await pb_get_all("chapters", {"filter": f"series_id='{series_id}'", "sort": "-chapter_number"})
        return chapters
    except Exception as e:
        logger.error(f"Error fetching chapters: {e}")
        return []

@router.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str):
    try:
        # 1. جلب الصفحات
        pages_data = await pb_get_all("pages", {"filter": f"chapter_id='{chapter_id}'", "sort": "page_number"})
        
        if not pages_data:
            raise HTTPException(status_code=404, detail="Chapter pages not found")
            
        # 2. جلب تفاصيل الفصل الحالي
        current_chap = await pb_get_one("chapters", chapter_id)
        if not current_chap:
             raise HTTPException(status_code=404, detail="Chapter details not found")

        series_id = current_chap.get('series_id')
        curr_num = current_chap.get('chapter_number')

        # 3. المنطق الذكي: جلب الفصل السابق (أكبر رقم أقل من الحالي)
        # مثال: أنا في فصل 10، أريد 9 (ترتيب تنازلي، آخذ الأول)
        prev_q = {
            "filter": f"series_id='{series_id}' && chapter_number < {curr_num}",
            "sort": "-chapter_number",
            "perPage": 1
        }
        prev_res = await pb_get_all("chapters", prev_q)
        prev_id = prev_res[0]['id'] if prev_res else None

        # 4. المنطق الذكي: جلب الفصل التالي (أصغر رقم أكبر من الحالي)
        # مثال: أنا في فصل 10، أريد 11 (ترتيب تصاعدي، آخذ الأول)
        next_q = {
            "filter": f"series_id='{series_id}' && chapter_number > {curr_num}",
            "sort": "chapter_number",
            "perPage": 1
        }
        next_res = await pb_get_all("chapters", next_q)
        next_id = next_res[0]['id'] if next_res else None

        image_urls = [f"/api/image/{p.get('file_id')}" for p in pages_data if p.get('file_id')]
        
        return {
            "pages": image_urls,
            "next_chapter": next_id,
            "prev_chapter": prev_id,
            "chapter_number": curr_num
        }
    except Exception as e:
        logger.error(f"Error in get_pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image/{file_id}")
async def proxy_image(file_id: str):
    real_url = await get_telegram_link(file_id)
    if not real_url:
        return RedirectResponse("https://via.placeholder.com/400?text=Image+Error")
    return RedirectResponse(real_url)