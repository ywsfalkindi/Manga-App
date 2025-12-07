# ================================================
# FILE: main.py
# ================================================
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import router as api_router
from app.services import init_client, close_client
from contextlib import asynccontextmanager
import uvicorn

# إدارة دورة حياة التطبيق (لإنشاء اتصال واحد مشترك)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # عند التشغيل: نفتح الاتصال
    init_client()
    yield
    # عند الإيقاف: نغلق الاتصال
    await close_client()

app = FastAPI(title="Manga Hub Pro", lifespan=lifespan)

# API Routes
app.include_router(api_router, prefix="/api")

# Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    # === تحسين 4: إيقاف reload لتحسين الأداء في الإنتاج ===
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)