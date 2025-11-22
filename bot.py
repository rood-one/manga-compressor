import os
import logging
import tempfile
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from image_downloader import download_images
from pdf_creator import create_compressed_pdf
from pdf_creator_high_quality import create_high_quality_pdf

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
    وسأقوم بتحميلها وضغطها وتحويلها إلى PDF

    المميزات:
    • دعم الصور الطويلة والكبيرة
    • خيارات ضغط متعددة
    • جودة عالية للصور الطويلة

    ⚡ للإعدادات السريعة: أرسل الرابط مباشرة
    🎛 للإعدادات المتقدمة: أرسل /quality ثم الرابط
    """
    await update.message.reply_text(welcome_text)

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خيارات الجودة"""
    quality_text = """
    🎛️ خيارات الجودة:

    ⚡ سريع (افتراضي) - ضغط جيد مع حجم معقول
    🎨 عالي - جودة أفضل مع حجم أكبر
    📄 أصغر - أقصى ضغط مع جودة أقل

    أرسل الرابط بعد اختيارك:
    مثال: ⚡ https://example.com/images/
    """
    await update.message.reply_text(quality_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية التي تحتوي على روابط"""
    user_input = update.message.text.strip()
    
    # تحديد نمط الجودة من الرسالة
    quality_mode = "balanced"  # افتراضي
    url = user_input
    
    if user_input.startswith('⚡ '):
        quality_mode = "balanced"
        url = user_input[2:].strip()
    elif user_input.startswith('🎨 '):
        quality_mode = "high"
        url = user_input[2:].strip()
    elif user_input.startswith('📄 '):
        quality_mode = "small"
        url = user_input[2:].strip()
    
    # التحقق من أن الرسالة تحتوي على رابط
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح يبدأ بـ http:// أو https://")
        return
    
    status_message = await update.message.reply_text("🔄 جاري معالجة طلبك...")
    
    try:
        await update.message.reply_text(f"⏳ جاري تحميل الصور... (وضع الجودة: {quality_mode})")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # تحميل الصور
            image_paths = download_images(url, temp_dir)
            
            if not image_paths:
                await status_message.edit_text("❌ لم أتمكن من العثور على أي صور في هذا الرابط")
                return
            
            # تحليل أبعاد الصور
            from PIL import Image
            total_height = 0
            for img_path in image_paths:
                try:
                    with Image.open(img_path) as img:
                        width, height = img.size
                        total_height += height
                        logging.info(f"📐 صورة {os.path.basename(img_path)}: {width}x{height}")
                except:
                    pass
            
            avg_height = total_height / len(image_paths) if image_paths else 0
            await status_message.edit_text(
                f"✅ تم تحميل {len(image_paths)} صورة\n"
                f"📏 متوسط الارتفاع: {avg_height:.0f} بكسل\n"
                f"⏳ جاري إنشاء PDF..."
            )
            
            pdf_path = os.path.join(temp_dir, "images.pdf")
            
            try:
                if quality_mode == "high":
                    # استخدام الجودة العالية
                    create_high_quality_pdf(image_paths, pdf_path)
                elif quality_mode == "small":
                    # استخدام الضغط القوي (الطريقة الأصلية)
                    create_compressed_pdf(image_paths, pdf_path)
                else:
                    # استخدام الطريقة المتوازنة
                    create_compressed_pdf(image_paths, pdf_path)
                    
            except Exception as pdf_error:
                logging.error(f"❌ خطأ في إنشاء PDF: {pdf_error}")
                await status_message.edit_text(
                    f"❌ حدث خطأ أثناء إنشاء PDF\n"
                    f"✅ تم تحميل {len(image_paths)} صورة\n"
                    f"💡 جرب وضع جودة مختلف"
                )
                return
            
            # التحقق من أن PDF تم إنشاؤه بنجاح
            if not os.path.exists(pdf_path):
                await status_message.edit_text("❌ فشل إنشاء ملف PDF")
                return
            
            # إرسال ملف PDF
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)
            
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    quality_emoji = "🎨" if quality_mode == "high" else "⚡" if quality_mode == "balanced" else "📄"
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=f"images_{quality_mode}_quality.pdf",
                        caption=f"{quality_emoji} تم الإنشاء بنجاح!\n"
                               f"حجم الملف: {file_size:.2f} MB\n"
                               f"عدد الصور: {len(image_paths)}\n"
                               f"وضع الجودة: {quality_mode}"
                    )
                
                await status_message.delete()
                
            except Exception as send_error:
                await status_message.edit_text(
                    f"✅ تم إنشاء PDF بنجاح لكن حدث خطأ في الإرسال\n"
                    f"حجم الملف: {file_size:.2f} MB\n"
                    f"💡 قد يكون الملف كبير جداً للبوت"
                )
            
    except Exception as e:
        logging.error(f"❌ خطأ عام: {e}")
        logging.error(traceback.format_exc())
        await status_message.edit_text("❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")

def main():
    if not BOT_TOKEN:
        logging.error("لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quality", handle_quality))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("🤖 البوت يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()
