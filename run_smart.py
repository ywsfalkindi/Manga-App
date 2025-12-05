import subprocess
import time
import re
import requests
import os
import signal
import sys

# ----------------- إعداداتك -----------------
# 🔴 ضع توكن البوت هنا
TELEGRAM_BOT_TOKEN = "8319175055:AAHvNflC34EurD-_z_0y5Kvh491UaHfO7MU"
# اسم الزر في تيليجرام
BUTTON_TEXT = "اقرأ المانجا 🐉"

# -------------------------------------------

def update_telegram_menu(new_url):
    """تحديث زر القائمة في تيليجرام تلقائياً"""
    print(f"🔄 جاري تحديث البوت بالرابط الجديد: {new_url}")
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setChatMenuButton"
    
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
    print("🚀 جاري تشغيل النظام الذكي...")

    # 1. تشغيل قاعدة البيانات (في الخلفية)
    print("📦 تشغيل PocketBase...")
    pb_process = subprocess.Popen(["pocketbase", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. تشغيل البايثون (في الخلفية)
    print("🐍 تشغيل FastAPI...")
    api_process = subprocess.Popen(["uvicorn", "main:app", "--reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
    
    # حلقة لقراءة السطور والبحث عن الرابط
    try:
        while True:
            line = cf_process.stdout.readline()
            if not line:
                break
            
            # طباعة السطور للتأكد (اختياري)
            # print(line.strip())

            # البحث عن رابط trycloudflare.com
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if match:
                tunnel_url = match.group(0)
                print(f"🔗 تم التقاط الرابط: {tunnel_url}")
                
                # 4. تحديث تيليجرام فوراً
                update_telegram_menu(tunnel_url)
                print("\n✨ النظام يعمل بالكامل! اضغط Ctrl+C للإيقاف.\n")
                
                # نتوقف عن قراءة السطور ونترك البرنامج يعمل
                break 
        
        # إبقاء البرنامج يعمل حتى يوقفه المستخدم
        cf_process.wait()

    except KeyboardInterrupt:
        print("\n🛑 جاري إيقاف الخدمات...")
        pb_process.terminate()
        api_process.terminate()
        cf_process.terminate()
        print("👋 تم الإغلاق بنجاح.")

if __name__ == "__main__":
    main()