import requests
import time
import os
from dotenv import load_dotenv

# [cite_start]تحميل التوكن من ملف .env لضمان الأمان [cite: 1]
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("🔴 خطأ: لم يتم العثور على التوكن في ملف .env")
    exit()

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Connection Error: {e}")
        return {}

print("🤖 البوت يعمل الآن... أرسل الصورة للبوت في تيليجرام وسأعطيك الكود فوراً!")

last_update_id = None
while True:
    updates = get_updates(last_update_id)
    if "result" in updates:
        for update in updates["result"]:
            last_update_id = update["update_id"] + 1
            
            if "message" in update and "photo" in update["message"]:
                photo = update["message"]["photo"][-1]
                file_id = photo["file_id"]
                
                print("\n📸 تم استلام صورة!")
                print(f"✅ File ID: {file_id}")
                print("-" * 30)
        
    time.sleep(1)