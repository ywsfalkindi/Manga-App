import os
import requests
from pocketbase import PocketBase

# ---------------- إعداداتك ----------------
# 1. توكن البوت الخاص بك
TELEGRAM_BOT_TOKEN = "8319175055:AAHvNflC34EurD-_z_0y5Kvh491UaHfO7MU"

# 2. الاتصال بـ PocketBase المحلي
pb = PocketBase("http://127.0.0.1:8090")

# ---------------- الوظائف ----------------

def send_photo_to_telegram(image_path):
    """يرسل صورة للبوت ويعيد الـ File ID"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    # نرسل الصورة إلى "نفس البوت" (نستخدم chat_id وهمي أو خاص بك، البوت يقبل الإرسال لنفسه أحياناً أو لقناة)
    # الأسهل هنا: سنرسلها لقناة خاصة أو لك أنت شخصياً
    # لكن لتبسيط الأمور: سنستخدم خدعة getUpdates التي استخدمناها سابقاً، أو نرسلها لـ chat_id الخاص بك
    # 🔴 لكي يعمل هذا السكربت، يجب أن تضع Chat ID خاص بك (يمكنك معرفته من @RawDataBot)
    chat_id = "1494578430" 
    
    with open(image_path, "rb") as img:
        payload = {"chat_id": chat_id}
        files = {"photo": img}
        resp = requests.post(url, data=payload, files=files).json()
        
    if resp["ok"]:
        # نأخذ أكبر حجم للصورة
        return resp["result"]["photo"][-1]["file_id"]
    else:
        print(f"❌ خطأ في تيليجرام: {resp}")
        return None

def upload_folder(folder_path, chapter_title, chapter_num):
    print(f"🚀 جاري رفع الفصل: {chapter_title}...")

    # 1. إنشاء الفصل في PocketBase
    chapter_data = {
        "title": chapter_title,
        "chapter_number": chapter_num
    }
    chapter = pb.collection("chapters").create(chapter_data)
    chapter_id = chapter.id
    print(f"✅ تم إنشاء الفصل (ID: {chapter_id})")

    # 2. قراءة الصور من المجلد
    files = sorted(os.listdir(folder_path)) # ترتيب الملفات (1.jpg, 2.jpg...)
    
    page_num = 1
    for filename in files:
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            file_path = os.path.join(folder_path, filename)
            print(f"   📤 جاري رفع الصفحة {page_num}: {filename}...")
            
            # أرسل لتيليجرام واحصل على ID
            file_id = send_photo_to_telegram(file_path)
            
            if file_id:
                # احفظ في PocketBase
                pb.collection("pages").create({
                    "chapter_id": chapter_id,
                    "file_id": file_id,
                    "page_number": page_num
                })
                print(f"      ✨ تم الحفظ!")
                page_num += 1
            else:
                print("      ⚠️ فشل الرفع!")

    print("\n🎉 انتهت العملية بنجاح!")

# ---------------- التشغيل ----------------

# 🔴 عدل هذا المسار لمجلد صور في جهازك
folder_location = r"C:\Users\MTC Admin\Desktop\DragonBall_Ch100" 

# تشغيل الدالة (اسم الفصل، رقم الفصل)
# upload_folder(folder_location, "قتال مورو الأسطوري", 2)