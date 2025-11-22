import os
import re
import tempfile
import logging
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from PIL import Image
import img2pdf

from telegram import Update, File
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات والثوابت ---
# يجب تغيير هذا إلى رمز البوت الخاص بك
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN") 
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "YOUR_TELEGRAM_USER_ID"))

# 💥 التعديل هنا: تعريف كائن التطبيق كمتغير عام 💥
# Gunicorn سيستورد هذا المتغير: bot:app
app = Application.builder().token(BOT_TOKEN).build()
# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- وظائف المساعدة ---

def get_image_url_list(base_url: str) -> list[str]:
    """
    يحاول استخراج عناوين URL للصور التي تبدأ بـ '001.jpg' تسلسليًا 
    عن طريق فحص الصفحة للحصول على الروابط. إذا فشل، يحاول التخمين بناءً على اسم الملف.
    """
    logger.info(f"جارٍ تحليل الصفحة: {base_url}")
    
    # 1. محاولة التحليل باستخدام BeautifulSoup
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # البحث عن أي عنصر (مثل <img>, <a>) يحتوي على رابط ينتهي بـ "001.jpg"
        initial_image_link = None
        for tag in soup.find_all(lambda tag: tag.has_attr('src') and '001.jpg' in tag['src'] or tag.has_attr('href') and '001.jpg' in tag['href']):
            link = tag.get('src') or tag.get('href')
            if '001.jpg' in link:
                initial_image_link = link
                break
        
        if initial_image_link:
            # محاولة بناء المسار التسلسلي
            # مثال: http://example.com/images/001.jpg -> http://example.com/images/
            base_image_path = initial_image_link.rsplit('/', 1)[0] + '/'
            image_urls = []
            
            # نفترض وجود 99 صورة كحد أقصى (يمكنك زيادتها)
            for i in range(1, 100):
                # تنسيق اسم الملف: 001.jpg, 002.jpg, ..., 010.jpg, ..., 099.jpg
                filename = f"{i:03d}.jpg" 
                image_url = base_image_path + filename
                
                # التحقق من وجود الصورة
                # نستخدم HEAD ليكون الطلب أسرع
                head_check = requests.head(image_url, timeout=5)
                if head_check.status_code == 200 and 'image' in head_check.headers.get('Content-Type', ''):
                    image_urls.append(image_url)
                else:
                    # توقف عندما لا نجد الصورة التسلسلية التالية
                    logger.info(f"لم يتم العثور على {image_url}. التوقف عند {i-1} صور.")
                    break
            
            return image_urls
        
    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ أثناء جلب أو تحليل الصفحة: {e}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في التحليل: {e}")
        
    return []


def download_and_compress_images(urls: list[str]) -> list[bytes]:
    """
    تقوم بتنزيل الصور من قائمة العناوين وضغطها بأقصى قدر ممكن (جودة JPEG 80).
    تعيد قائمة بـ BytesIO streams للصور المضغوطة.
    """
    compressed_images = []
    
    for i, url in enumerate(urls):
        try:
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            
            # استخدام BytesIO للعمل مع البيانات في الذاكرة
            image_stream = BytesIO(response.content)
            img = Image.open(image_stream)
            
            # تحويل الصورة إلى RGB إذا لم تكن كذلك (مهم للـ JPEG و img2pdf)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # ضغط الصورة: حفظها كـ JPEG مع جودة 80 (ضغط جيد مع جودة مقبولة)
            compressed_stream = BytesIO()
            img.save(compressed_stream, format="JPEG", quality=80, optimize=True)
            compressed_images.append(compressed_stream.getvalue())
            
            logger.info(f"تم ضغط الصورة {i+1} بنجاح من {url}")

        except requests.exceptions.RequestException as e:
            logger.error(f"فشل تنزيل الصورة من {url}: {e}")
            continue
        except Exception as e:
            logger.error(f"خطأ أثناء معالجة الصورة {url}: {e}")
            continue
            
    return compressed_images

# --- معالجات التليجرام ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /start."""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("عذراً، هذا البوت مخصص لمستخدمين محددين فقط.")
        return
        
    await update.message.reply_text(
        "مرحباً! أرسل لي **رابط صفحة الويب** التي تحتوي على صور تسلسلية تبدأ بـ `001.jpg`.\n"
        "سأقوم بتحميل جميع الصور التسلسلية، ضغطها، وتجميعها في ملف PDF صغير وإرساله إليك."
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسالة المستخدم التي تحتوي على رابط صفحة الويب."""
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER_ID:
        logger.warning(f"محاولة استخدام غير مصرح بها من ID: {user_id}")
        await update.message.reply_text("عذراً، هذا البوت مخصص لمستخدمين محددين فقط.")
        return

    url = update.message.text.strip()

    # تحقق بسيط من شكل الرابط
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("الرجاء إرسال رابط صحيح يبدأ بـ `http://` أو `https://`.")
        return

    message = await update.message.reply_text(f"جاري معالجة الرابط: `{url}`. قد تستغرق العملية بعض الوقت...")

    try:
        # 1. الحصول على قائمة عناوين URL للصور
        image_urls = get_image_url_list(url)
        
        if not image_urls:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
                text="❌ لم يتم العثور على أي صور تبدأ بـ `001.jpg` تسلسليًا في هذه الصفحة.\n"
                     "تأكد من أن الرابط صحيح وأن الصور متوفرة بشكل تسلسلي."
            )
            return

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            text=f"✅ تم العثور على **{len(image_urls)}** صور. جاري التنزيل والضغط..."
        )

        # 2. تنزيل وضغط الصور
        compressed_image_bytes = download_and_compress_images(image_urls)
        
        if not compressed_image_bytes:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
                text="⚠️ فشل في تنزيل أو ضغط جميع الصور. يرجى المحاولة مرة أخرى."
            )
            return

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            text="⏳ جاري تجميع الصور في ملف PDF بأقصى ضغط ممكن..."
        )

        # 3. إنشاء ملف PDF باستخدام img2pdf (فعال جداً في إنشاء PDF صغير الحجم من صور JPEG)
        pdf_bytes = img2pdf.convert(compressed_image_bytes)
        
        # 4. حفظ ملف PDF مؤقتًا للإرسال (ضروري أحياناً للـ API)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            tmp_pdf.write(pdf_bytes)
            tmp_pdf_path = tmp_pdf.name

        # 5. إرسال ملف PDF
        await update.message.reply_document(
            document=tmp_pdf_path,
            filename="compressed_images.pdf",
            caption=f"تم إنشاء ملف PDF بنجاح! ({len(compressed_image_bytes)} صورة)"
        )

        # 6. حذف الملف المؤقت بعد الإرسال
        os.remove(tmp_pdf_path)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id) # حذف رسالة 'جاري المعالجة'
        
    except Exception as e:
        logger.error(f"حدث خطأ كبير: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            text=f"🚫 حدث خطأ غير متوقع أثناء المعالجة: {e}"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يسجل الأخطاء التي تسببها التحديثات."""
    logger.error("حدث خطأ:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("عذراً، حدث خطأ داخلي. يرجى التحقق من الرابط والمحاولة مرة أخرى.")

# --- نقطة الدخول الرئيسية ---

def main():
    """تشغيل البوت."""
    
    # Render يتطلب أن يستمع التطبيق على منفذ (Port) كخدمة ويب
    # لذلك، سنستخدم طريقة Webhook بدلاً من Polling إذا تم توفير متغيرات البيئة.
    
    
    PORT = int(os.environ.get('PORT', 8080))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
        logger.error("الرجاء تحديد BOT_TOKEN في متغيرات البيئة أو استبدال القيمة الافتراضية.")
        return

    # 1. تسجيل المعالجات (نستخدم المتغير app العام الآن)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_error_handler(error_handler)

    if WEBHOOK_URL:
        # تشغيل كـ Webhook (مطلوب لـ Render)
        logger.info(f"تشغيل البوت كـ Webhook على المنفذ {PORT}")
        # 2. بدء تشغيل Webhook باستخدام الكائن app العام
        app.run_webhook( 
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        # تشغيل كـ Polling (للتجربة المحلية)
        logger.info("تشغيل البوت كـ Polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
