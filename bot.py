import os
import tempfile
import logging
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from PIL import Image
import img2pdf

# 🚨 Imports محدثة لـ PTB v20 🚨
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from typing import Optional

# --- الإعدادات والثوابت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN") 
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "YOUR_TELEGRAM_USER_ID"))

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- وظائف المساعدة ---

def get_image_url_list(base_url: str) -> list[str]:
    """
    تحليل الصفحة لاستخراج عناوين URL للصور التي تبدأ بـ '001.jpg' تسلسليًا (001.jpg, 002.jpg, ...).
    """
    logger.info(f"جارٍ تحليل الصفحة: {base_url}")
    image_urls = []
    
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        initial_image_link = None
        # البحث عن رابط الصورة الأول (001.jpg)
        for tag in soup.find_all(lambda tag: tag.has_attr('src') and '001.jpg' in tag['src'] or tag.has_attr('href') and '001.jpg' in tag['href']):
            link = tag.get('src') or tag.get('href')
            if '001.jpg' in link:
                initial_image_link = link
                break
        
        if initial_image_link:
            # بناء المسار التسلسلي
            base_image_path = initial_image_link.rsplit('/', 1)[0] + '/'
            
            # التحقق من 1 إلى 99 صورة
            for i in range(1, 100):
                filename = f"{i:03d}.jpg" 
                image_url = base_image_path + filename
                
                # التحقق السريع من وجود الصورة (باستخدام HEAD)
                head_check = requests.head(image_url, timeout=5)
                if head_check.status_code == 200 and 'image' in head_check.headers.get('Content-Type', ''):
                    image_urls.append(image_url)
                else:
                    logger.info(f"لم يتم العثور على {image_url}. التوقف.")
                    break
            
    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ أثناء جلب أو تحليل الصفحة: {e}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في التحليل: {e}")
        
    return image_urls


def download_and_compress_images(urls: list[str]) -> list[bytes]:
    """
    تنزيل الصور وضغطها كـ JPEG بجودة 80.
    """
    compressed_images = []
    
    for i, url in enumerate(urls):
        try:
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            
            image_stream = BytesIO(response.content)
            img = Image.open(image_stream)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # الضغط: حفظ كـ JPEG بجودة 80
            compressed_stream = BytesIO()
            img.save(compressed_stream, format="JPEG", quality=80, optimize=True)
            compressed_images.append(compressed_stream.getvalue())
            
            logger.info(f"تم ضغط الصورة {i+1} بنجاح.")

        except requests.exceptions.RequestException as e:
            logger.error(f"فشل تنزيل الصورة من {url}: {e}")
            continue
        except Exception as e:
            logger.error(f"خطأ أثناء معالجة الصورة {url}: {e}")
            continue
            
    return compressed_images

# --- معالجات التليجرام محدثة ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /start."""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("عذراً، هذا البوت مخصص لمستخدمين محددين فقط.")
        return
        
    await update.message.reply_text(
        "مرحباً! أرسل لي **رابط صفحة الويب** التي تحتوي على صور تسلسلية تبدأ بـ `001.jpg`.\n"
        "سأقوم بتحميل جميع الصور، ضغطها، وتجميعها في ملف PDF صغير وإرساله إليك."
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسالة المستخدم التي تحتوي على رابط صفحة الويب."""
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER_ID:
        logger.warning(f"محاولة استخدام غير مصرح بها من ID: {user_id}")
        await update.message.reply_text("عذراً، هذا البوت مخصص لمستخدمين محددين فقط.")
        return

    url = update.message.text.strip()
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("الرجاء إرسال رابط صحيح.")
        return

    message = await update.message.reply_text(f"جاري معالجة الرابط: `{url}`. يرجى الانتظار...")

    try:
        image_urls = get_image_url_list(url)
        
        if not image_urls:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
                text="❌ لم يتم العثور على أي صور تبدأ بـ `001.jpg` تسلسليًا."
            )
            return

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            text=f"✅ تم العثور على **{len(image_urls)}** صور. جاري التنزيل والضغط..."
        )

        compressed_image_bytes = download_and_compress_images(image_urls)
        
        if not compressed_image_bytes:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
                text="⚠️ فشل في تنزيل أو ضغط جميع الصور."
            )
            return

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            text="⏳ جاري تجميع الصور في ملف PDF..."
        )

        pdf_bytes = img2pdf.convert(compressed_image_bytes)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            tmp_pdf.write(pdf_bytes)
            tmp_pdf_path = tmp_pdf.name

        await update.message.reply_document(
            document=open(tmp_pdf_path, 'rb'),
            filename="compressed_images.pdf",
            caption=f"تم إنشاء ملف PDF بنجاح! ({len(compressed_image_bytes)} صورة)"
        )

        os.remove(tmp_pdf_path)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id) 
        
    except Exception as e:
        logger.error(f"حدث خطأ كبير: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            text=f"🚫 حدث خطأ غير متوقع أثناء المعالجة."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يسجل الأخطاء التي تسببها التحديثات."""
    logger.error("حدث خطأ:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("عذراً، حدث خطأ داخلي. يرجى التحقق من الرابط والمحاولة مرة أخرى.")

# --- نقطة الدخول الرئيسية محدثة ---
def main():
    PORT = int(os.environ.get('PORT', 8080))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
        logger.error("الرجاء تحديد BOT_TOKEN في متغيرات البيئة أو استبدال القيمة الافتراضية.")
        return

    # 🚨 استخدام Application بدلاً من Updater 🚨
    application = Application.builder().token(BOT_TOKEN).build()

    # تسجيل المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_error_handler(error_handler)

    if WEBHOOK_URL:
        logger.info(f"تشغيل البوت كـ Webhook على المنفذ {PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            secret_token=None  # يمكنك إضافة secret token إذا أردت
        )
    else:
        logger.info("تشغيل البوت كـ Polling...")
        application.run_polling()

if __name__ == "__main__":
    main()
