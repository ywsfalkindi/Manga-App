import requests
import time

# 🔴 ضع توكن البوت الخاص بك هنا
TOKEN = "8319175055:AAHvNflC34EurD-_z_0y5Kvh491UaHfO7MU"

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    response = requests.get(url, params=params)
    return response.json()

print("🤖 البوت يعمل الآن... أرسل الصورة للبوت في تيليجرام وسأعطيك الكود فوراً!")

last_update_id = None
while True:
    updates = get_updates(last_update_id)
    if "result" in updates:
        for update in updates["result"]:
            last_update_id = update["update_id"] + 1
            
            # إذا كانت الرسالة صورة
            if "message" in update and "photo" in update["message"]:
                # نأخذ أكبر حجم للصورة (آخر واحدة في القائمة)
                photo = update["message"]["photo"][-1]
                file_id = photo["file_id"]
                
                print("\n📸 تم استلام صورة!")
                print(f"✅ انسخ هذا الكود وضعه في PocketBase:")
                print(f"{file_id}")
                print("-" * 30)
            
    time.sleep(1)