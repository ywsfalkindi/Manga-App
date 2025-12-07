from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from .services import pb_get_all, pb_get_one, get_telegram_link
import logging

# إعداد سجل الأخطاء لنرى المشكلة في التيرمينال
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/series")
async def get_series(q: str = ""):
    try:
        # تجهيز الفلتر
        filter_query = {"filter": f"title ~ '{q}'"} if q else {"sort": "-updated"}
        
        # محاولة جلب البيانات
        items = await pb_get_all("series", filter_query)
        
        # إذا لم ترجع أي بيانات
        if not items:
            return []

        # معالجة كل عنصر
        cleaned_items = []
        for item in items:
            # استخدام .get لتجنب الخطأ إذا كان الحقل غير موجود
            cover_id = item.get('cover_file_id') 
            
            # إذا لم يوجد معرف صورة، نضع صورة افتراضية
            if cover_id:
                item['cover_url'] = f"/api/image/{cover_id}"
            else:
                # صورة رمادية افتراضية
                item['cover_url'] = "https://via.placeholder.com/300x450?text=No+Cover"
            
            cleaned_items.append(item)
            
        return cleaned_items

    except Exception as e:
        # طباعة الخطأ الحقيقي في التيرمينال
        logger.error(f"CRITICAL ERROR in get_series: {e}")
        # إعادة القائمة فارغة بدلاً من تحطيم الموقع بـ 500
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chapters/{series_id}")
async def get_chapters(series_id: str):
    try:
        chapters = await pb_get_all("chapters", {"filter": f"series_id='{series_id}'", "sort": "-chapter_number"})
        return chapters
    except Exception as e:
        logger.error(f"Error fetching chapters: {e}")
        return []

@router.get("/pages/{chapter_id}")
async def get_pages(chapter_id: str):
    try:
        pages_data = await pb_get_all("pages", {"filter": f"chapter_id='{chapter_id}'", "sort": "page_number"})
        
        if not pages_data:
            raise HTTPException(status_code=404, detail="Chapter not found")
            
        current_chap = await pb_get_one("chapters", chapter_id)
        if not current_chap:
             raise HTTPException(status_code=404, detail="Chapter details not found")

        # منطق التالي والسابق
        all_chaps = await pb_get_all("chapters", {
            "filter": f"series_id='{current_chap.get('series_id')}'", 
            "sort": "-chapter_number",
            "fields": "id,chapter_number"
        })
        
        curr_idx = next((i for i, c in enumerate(all_chaps) if c['id'] == chapter_id), -1)
        next_id = all_chaps[curr_idx - 1]['id'] if curr_idx > 0 else None
        prev_id = all_chaps[curr_idx + 1]['id'] if curr_idx < len(all_chaps) - 1 else None

        image_urls = [f"/api/image/{p.get('file_id')}" for p in pages_data if p.get('file_id')]
        
        return {
            "pages": image_urls,
            "next_chapter": next_id,
            "prev_chapter": prev_id,
            "chapter_number": current_chap.get('chapter_number')
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