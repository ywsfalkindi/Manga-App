from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    POCKETBASE_URL: str
    
    # نجعل هذا اختياري لتجنب الخطأ إذا لم يكن موجوداً
    SECRET_KEY: Optional[str] = None
    
    # إعدادات Pydantic
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"  # <--- هذا السطر هو الحل، يخبره بتجاهل أي متغير غريب في ملف .env
    )

settings = Settings()