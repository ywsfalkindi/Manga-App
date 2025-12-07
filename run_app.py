# ================================================
# FILE: run_app.py
# ================================================
import subprocess
import time
import re
import os
import sys
import threading
import signal
import platform

# ==========================================
# إعدادات التشغيل
# ==========================================
# === تحسين 5: كشف نظام التشغيل تلقائياً ===
if platform.system() == "Windows":
    PB_EXEC = "pocketbase.exe"
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
else:
    PB_EXEC = "./pocketbase"
    creation_flags = 0 # Not used in Linux
    
    # التأكد من صلاحية التنفيذ في لينكس
    if os.path.exists(PB_EXEC):
        os.chmod(PB_EXEC, 0o755)

PYTHON_EXEC = sys.executable
CLOUDFLARE_CMD = ["cloudflared", "tunnel", "--url", "http://localhost:8000"]

# تخزين العمليات لإغلاقها لاحقاً
processes = []

def log(msg, color="white"):
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    c = colors.get(color, colors["reset"])
    print(f"{c}[SYSTEM] {msg}{colors['reset']}")

def run_process(command, name):
    """تشغيل عملية في الخلفية"""
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creation_flags
        )
        processes.append(proc)
        log(f"تم تشغيل {name} بنجاح (PID: {proc.pid})", "green")
        return proc
    except FileNotFoundError:
        log(f"خطأ: الملف التنفيذي غير موجود للأمر: {command}", "red")
        return None

def monitor_cloudflare(proc):
    """مراقبة مخرجات كلاود فلير لاقتناص الرابط"""
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    
    log("جاري انتظار رابط Cloudflare...", "yellow")
    
    while True:
        line = proc.stderr.readline()
        if not line:
            break
        
        match = url_pattern.search(line)
        if match:
            public_url = match.group(0)
            log("="*50, "cyan")
            log(f"🔗 الرابط الجديد: {public_url}", "cyan")
            log("="*50, "cyan")
            
            with open("url.txt", "w") as f:
                f.write(public_url)
            log("تم حفظ الرابط في ملف url.txt", "green")
            log("✅ الموقع جاهز للعمل فوراً!", "green")
            break

def cleanup(signum, frame):
    """إغلاق جميع البرامج عند الخروج"""
    log("\nجاري إغلاق الأنظمة...", "red")
    for proc in processes:
        if platform.system() == "Windows":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(proc.pid)])
        else:
            proc.terminate()
    sys.exit(0)

# ==========================================
# التشغيل الرئيسي
# ==========================================
if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)

    print(r"""
    __  __                         _    _       _     
   |  \/  |                       | |  | |     | |    
   | \  / | __ _ _ __   __ _  __ _| |__| |_   _| |__  
   | |\/| |/ _` | '_ \ / _` |/ _` |  __  | | | | '_ \ 
   | |  | | (_| | | | | (_| | (_| | |  | | |_| | |_) |
   |_|  |_|\__,_|_| |_|\__, |\__,_|_|  |_|\__,_|_.__/ 
                        __/ |                         
                       |___/                          
    """)

    # 1. تشغيل PocketBase
    log("بدء تشغيل قاعدة البيانات...", "yellow")
    run_process([PB_EXEC, "serve"], "PocketBase")
    time.sleep(2)

    # 2. تشغيل الموقع (Backend)
    log("بدء تشغيل السيرفر (FastAPI)...", "yellow")
    run_process([PYTHON_EXEC, "main.py"], "Main App")

    # 3. تشغيل البوت
    log("بدء تشغيل بوت تيليجرام...", "yellow")
    run_process([PYTHON_EXEC, "bot.py"], "Telegram Bot")

    # 4. تشغيل Cloudflare Tunnel
    log("بدء تشغيل Cloudflare Tunnel...", "yellow")
    cf_proc = run_process(CLOUDFLARE_CMD, "Cloudflare")

    if cf_proc:
        threading.Thread(target=monitor_cloudflare, args=(cf_proc,), daemon=True).start()

    log("🚀 النظام يعمل بالكامل! اضغط Ctrl+C للإيقاف.", "green")

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            cleanup(None, None)