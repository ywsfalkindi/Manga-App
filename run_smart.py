import subprocess
import time
import re
import requests
import os
import signal
import sys

# ----------------- إعداداتك -----------------
# 🔴 ضع توكن البوت هنا
# TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # يجب أن يكون في ملف .env
# اسم الزر في تيليجرام
BUTTON_TEXT = "اقرأ المانجا 🐉"

# -------------------------------------------

def update_telegram_menu(new_url):
    """تحديث زر القائمة في تيليجرام تلقائياً"""
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة. لا يمكن تحديث زر القائمة.")
        return
    print(f"🔄 جاري تحديث البوت بالرابط الجديد: {new_url}")
    
    api_url = f"https://api.telegram.org/bot{telegram_bot_token}/setChatMenuButton"
    
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": BUTTON_TEXT,
            "web_app": {"url": new_url}
        }
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        if resp.json().get("ok"):
            print("✅ تم تحديث البوت بنجاح! افتح جوالك الآن.")
        else:
            print(f"❌ فشل تحديث البوت: {resp.text}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال بتيليجرام: {e}")

def main():
    # تحميل متغيرات البيئة من ملف .env
    from dotenv import load_dotenv
    load_dotenv()

    print("🚀 جاري تشغيل النظام الذكي...")

    # 1. تشغيل قاعدة البيانات (في الخلفية)
    print("📦 تشغيل PocketBase...")
    pb_process = subprocess.Popen(["pocketbase", "serve"])
    time.sleep(2) # إعطاء PocketBase بعض الوقت للبدء

    # 2. تشغيل البايثون (في الخلفية)
    print("🐍 تشغيل FastAPI...")
    api_process = subprocess.Popen(["uvicorn", "main:app", "--reload"], stdout=sys.stdout, stderr=sys.stderr)

    # 3. تشغيل Cloudflare وسحب الرابط
    print("☁️  تشغيل Cloudflare Tunnel...")
    # نشغل cloudflare ونقرأ المخرجات لنصطاد الرابط
    cf_process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8', 
        errors='ignore' 
    )

    tunnel_url = None
    url_found = False
    
    # حلقة لقراءة السطور والبحث عن الرابط
    try:
        while True:
            line = cf_process.stdout.readline()
            if not line:
                # إذا انتهت عملية cloudflared بشكل غير متوقع
                print("❌ Cloudflare Tunnel process exited unexpectedly.")
                break 
            
            print(line.strip()) # طباعة مخرجات cloudflared للمراقبة

            if not url_found: # البحث عن الرابط فقط إذا لم يتم العثور عليه بعد
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    tunnel_url = match.group(0)
                    print(f"🔗 تم التقاط الرابط: {tunnel_url}")
                    update_telegram_menu(tunnel_url)
                    print("\n✨ النظام يعمل بالكامل! اضغط Ctrl+C للإيقاف.\n")
                    url_found = True
        
        # إبقاء البرنامج يعمل حتى يوقفه المستخدم
        # إذا خرجنا من الحلقة (أي أن cloudflared توقف)، ننتظر للتأكد من إنهاء العملية
        if not url_found: # إذا لم يتم العثور على الرابط وخرجنا من الحلقة، فهذا يعني مشكلة
            cf_process.wait()

    except KeyboardInterrupt:
        print("\n🛑 جاري إيقاف الخدمات...")
        print("   - إيقاف PocketBase...")
        pb_process.terminate()
        print("   - إيقاف FastAPI...")
        api_process.terminate()
        print("   - إيقاف Cloudflare Tunnel...")
        cf_process.terminate()

        # انتظر حتى يتم إنهاء العمليات بالكامل لضمان عدم ترك أي شيء يعمل في الخلفية
        pb_process.wait()
        api_process.wait()
        cf_process.wait()
        print("👋 تم الإغلاق بنجاح.")

if __name__ == "__main__":
    main()