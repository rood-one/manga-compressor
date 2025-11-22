import os
import logging
import tempfile
import traceback
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
        await update.message.reply_text("⏳ جاري تحميل الصفحة والبحث عن الصور... (قد يستغرق 10-20 ثانية)")
        
        # إنشاء مجلد مؤقت للعمل
        with tempfile.TemporaryDirectory() as temp_dir:
            # تحميل الصور
            image_paths = download_images(url, temp_dir)
            
            if not image_paths:
                await status_message.edit_text(
                    "❌ لم أتمكن من العثور على أي صور في هذا الرابط\n\n"
                    "🔍 حاول:\n"
                    "• التأكد من أن الرابط صحيح\n"
                    "• أن الصفحة تحتوي على صور مرئية\n"
                    "• إرسال رابط مباشر للمجلد إن أمكن\n"
                    "• التأكد من أن الصور ليست محمية"
                )
                return
            
            await status_message.edit_text(f"✅ تم تحميل {len(image_paths)} صورة\n⏳ جاري ضغط الصور وإنشاء PDF... (قد يستغرق دقيقة)")
            
            # إنشاء ملف PDF مضغوط
            pdf_path = os.path.join(temp_dir, "compressed_images.pdf")
            
            try:
                create_compressed_pdf(image_paths, pdf_path)
            except Exception as pdf_error:
                logging.error(f"خطأ في إنشاء PDF: {pdf_error}")
                await status_message.edit_text(
                    f"❌ حدث خطأ أثناء إنشاء PDF\n"
                    f"✅ تم تحميل {len(image_paths)} صورة لكن لا يمكن تحويلها\n"
                    f"📧 قد تكون الصور تالفة أو غير مدعومة"
                )
                return
            
            # التحقق من أن PDF تم إنشاؤه بنجاح
            if not os.path.exists(pdf_path):
                await status_message.edit_text("❌ فشل إنشاء ملف PDF")
                return
            
            # إرسال ملف PDF
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # الحجم بالميجابايت
            
            if file_size > 50:  # إذا كان الملف أكبر من 50 ميجابايت
                await status_message.edit_text(
                    f"📁 حجم الملف كبير جداً ({file_size:.1f} MB)\n"
                    f"💡 جاري تقسيم الملف..."
                )
                # هنا يمكن إضافة منطق لتقسيم الملف إذا لزم الأمر
            
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename="compressed_images.pdf",
                        caption=f"📊 تم الإنشاء بنجاح!\nحجم الملف: {file_size:.2f} MB\nعدد الصور: {len(image_paths)}"
                    )
                
                await status_message.delete()
                
            except Exception as send_error:
                logging.error(f"خطأ في إرسال الملف: {send_error}")
                await status_message.edit_text(
                    f"✅ تم إنشاء PDF بنجاح لكن حدث خطأ في الإرسال\n"
                    f"حجم الملف: {file_size:.2f} MB\n"
                    f"💡 قد يكون الملف كبير جداً للبوت"
                )
            
    except Exception as e:
        logging.error(f"❌ خطأ عام: {e}")
        logging.error(traceback.format_exc())
        
        error_message = "❌ حدث خطأ غير متوقع أثناء المعالجة."
        
        # رسائل خطأ أكثر تحديداً
        if "memory" in str(e).lower():
            error_message += "\n💾 مشكلة في الذاكرة، جرب برابط به صور أقل."
        elif "timeout" in str(e).lower():
            error_message += "\n⏰ انتهت المهلة، جرب رابطاً آخر."
        elif "connection" in str(e).lower():
            error_message += "\n🌐 مشكلة في الاتصال، تأكد من الرابط."
        
        error_message += "\n🔄 يرجى المحاولة مرة أخرى."
        
        await status_message.edit_text(error_message)

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
    logging.info("🤖 البوت يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()
