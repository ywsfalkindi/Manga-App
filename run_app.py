import subprocess
import time
import re
import os
import sys
import threading
import signal

# ==========================================
# إعدادات التشغيل
# ==========================================
# تأكد أن اسم ملف بوكيت بيس صحيح (قد يكون pocketbase.exe في ويندوز)
PB_EXEC = "pocketbase.exe" if os.name == 'nt' else "./pocketbase"
PYTHON_EXEC = sys.executable  # يستخدم نفس نسخة بايثون الحالية
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
        # shell=False أكثر أماناً وتحكماً في العمليات
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
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
        
        # البحث عن الرابط
        match = url_pattern.search(line)
        if match:
            public_url = match.group(0)
            log("="*50, "cyan")
            log(f"🔗 الرابط الجديد: {public_url}", "cyan")
            log("="*50, "cyan")
            
            # حفظ الرابط في ملف نصي لسهولة الوصول
            with open("url.txt", "w") as f:
                f.write(public_url)
            log("تم حفظ الرابط في ملف url.txt", "green")
            
            # (اختياري) بما أن الكود الجديد يستخدم مسارات نسبية،
            # لا حاجة لتعديل ملفات JS. الموقع يعمل تلقائياً!
            log("✅ الموقع جاهز للعمل فوراً!", "green")
            break

def cleanup(signum, frame):
    """إغلاق جميع البرامج عند الخروج"""
    log("\nجاري إغلاق الأنظمة...", "red")
    for proc in processes:
        if os.name == 'nt':
            # أمر خاص لويندوز لقتل شجرة العمليات
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(proc.pid)])
        else:
            proc.terminate()
    sys.exit(0)

# ==========================================
# التشغيل الرئيسي
# ==========================================
if __name__ == "__main__":
    # ربط زر Ctrl+C بدالة التنظيف
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
    time.sleep(2) # انتظار قليل لتجهيز القاعدة

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
        # تشغيل خيط (Thread) لمراقبة الرابط دون تجميد البرنامج
        threading.Thread(target=monitor_cloudflare, args=(cf_proc,), daemon=True).start()

    log("🚀 النظام يعمل بالكامل! اضغط Ctrl+C للإيقاف.", "green")

    # إبقاء السكريبت يعمل
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            cleanup(None, None)