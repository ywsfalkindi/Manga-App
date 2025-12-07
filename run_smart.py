import subprocess
import time
import re
import requests
import os
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

BUTTON_TEXT = "اقرأ المانجا 🐉"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def update_telegram_menu(new_url):
    if not TOKEN:
        print("❌ لم يتم العثور على التوكن في .env")
        return
    
    api_url = f"https://api.telegram.org/bot{TOKEN}/setChatMenuButton"
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": BUTTON_TEXT,
            "web_app": {"url": new_url}
        }
    }
    try:
        requests.post(api_url, json=payload, timeout=10)
        print("✅ تم تحديث زر البوت في تيليجرام!")
    except:
        print("⚠️ فشل تحديث الزر (تأكد من الإنترنت)")

def main():
    print("🚀 جاري تشغيل النظام...")

    # 1. PocketBase
    pb_proc = subprocess.Popen(["pocketbase", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("📦 PocketBase يعمل.")

    # 2. FastAPI
    api_proc = subprocess.Popen(["uvicorn", "main:app", "--port", "8000"], stdout=sys.stdout, stderr=sys.stderr)
    print("🐍 FastAPI يعمل.")
    time.sleep(2)

    # 3. Cloudflare Tunnel
    print("☁️ جاري إنشاء النفق...")
    cf_proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore'
    )

    tunnel_url = None
    try:
        while True:
            line = cf_proc.stdout.readline()
            if not line: break
            
            # البحث عن الرابط
            if "trycloudflare.com" in line and not tunnel_url:
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    tunnel_url = match.group(0)
                    print(f"\n🔗 الرابط الجديد: {tunnel_url}")
                    update_telegram_menu(tunnel_url)
                    print("\n✨ النظام جاهز! اضغط Ctrl+C للإيقاف.\n")
            
            # طباعة الأخطاء فقط
            if "error" in line.lower(): print(line.strip())

    except KeyboardInterrupt:
        print("\n🛑 إيقاف التشغيل...")
        pb_proc.terminate()
        api_proc.terminate()
        cf_proc.terminate()
        print("👋 وداعاً")

if __name__ == "__main__":
    main()