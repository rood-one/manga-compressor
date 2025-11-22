import os
import logging
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from image_downloader import download_images
from pdf_creator import create_compressed_pdf

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /start"""
    welcome_text = """
    🖼️ مرحباً! أنا بوت تحويل الصور إلى PDF 📄
    
    أرسل لي رابط الموقع الذي يحتوي على الصور
    وسأقوم بتحميلها وضغطها وتحويلها إلى PDF بأصغر حجم ممكن!
    
    المميزات:
    • انتظار تحميل الصفحة بالكامل
    • البحث عن الصور بطرق متعددة
    • ضغط متقدم للصور
    • تحويل إلى PDF بحجم صغير
    
    ⏰ قد تستغرق العملية 10-30 ثانية
    """
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية التي تحتوي على روابط"""
    url = update.message.text.strip()
    
    # التحقق من أن الرسالة تحتوي على رابط
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح يبدأ بـ http:// أو https://")
        return
    
    # إرسال رسالة تظهر أن البوت يعمل
    status_message = await update.message.reply_text("🔄 جاري معالجة طلبك...")
    
    try:
        await update.message.reply_text("⏳ جاري تحميل الصفحة والبحث عن الصور...")
        
        # إنشاء مجلد مؤقت للعمل
        with tempfile.TemporaryDirectory() as temp_dir:
            # تحميل الصور
            image_paths = download_images(url, temp_dir)
            
            if not image_paths:
                await status_message.edit_text("❌ لم أتمكن من العثور على أي صور في هذا الرابط\n\n🔍 حاول:\n• التأكد من أن الرابط صحيح\n• أن الصفحة تحتوي على صور\n• إرسال رابط مباشر للمجلد إن أمكن")
                return
            
            await status_message.edit_text(f"✅ تم تحميل {len(image_paths)} صورة\n⏳ جاري ضغط الصور وإنشاء PDF...")
            
            # إنشاء ملف PDF مضغوط
            pdf_path = os.path.join(temp_dir, "compressed_images.pdf")
            create_compressed_pdf(image_paths, pdf_path)
            
            # إرسال ملف PDF
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # الحجم بالميجابايت
            
            await update.message.reply_document(
                document=open(pdf_path, 'rb'),
                filename="compressed_images.pdf",
                caption=f"📊 تم الإنشاء بنجاح!\nحجم الملف: {file_size:.2f} MB\nعدد الصور: {len(image_paths)}"
            )
            
            await status_message.delete()
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await status_message.edit_text("❌ حدث خطأ أثناء المعالجة. يرجى المحاولة مرة أخرى أو تجربة رابط آخر.")

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    if not BOT_TOKEN:
        logging.error("لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
        return
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # بدء البوت
    application.run_polling()

if __name__ == '__main__':
    main()
