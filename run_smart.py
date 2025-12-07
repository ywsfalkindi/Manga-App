import subprocess
import time
import re
import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def update_telegram_menu(new_url):
    if not TOKEN: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/setChatMenuButton",
            json={
                "menu_button": {
                    "type": "web_app", 
                    "text": "اقرأ المانجا 🐉", 
                    "web_app": {"url": new_url}
                }
            },
            timeout=10
        )
        print("✅ تم تحديث زر البوت!")
    except: print("⚠️ فشل تحديث الزر")

def main():
    print("🚀 جاري تشغيل النظام السريع...")

    # 1. PocketBase
    pb_proc = subprocess.Popen(["pocketbase", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("📦 PocketBase يعمل.")

    # 2. FastAPI
    # تمرير متغيرات البيئة الحالية للتطبيق
    env = os.environ.copy()
    api_proc = subprocess.Popen(
        ["uvicorn", "main:app", "--port", "8000"], 
        stdout=sys.stdout, 
        stderr=sys.stderr,
        env=env
    )
    print("⚡ FastAPI يعمل.")
    time.sleep(2)

    # 3. Cloudflare Tunnel
    print("☁️ جاري فتح النفق...")
    cf_proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore'
    )

    tunnel_url = None
    try:
        while True:
            line = cf_proc.stdout.readline()
            if not line: break
            
            if "trycloudflare.com" in line and not tunnel_url:
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    tunnel_url = match.group(0)
                    print(f"\n🔗 الرابط: {tunnel_url}")
                    update_telegram_menu(tunnel_url)
                    print("\n✨ النظام جاهز! (Ctrl+C للإيقاف)\n")
    except KeyboardInterrupt:
        print("\n🛑 إيقاف...")
        pb_proc.terminate()
        api_proc.terminate()
        cf_proc.terminate()

if __name__ == "__main__":
    main()