import img2pdf
from PIL import Image, ImageFile
import os
import logging
import traceback

# السماح بتحميل الصور التالفة جزئياً
ImageFile.LOAD_TRUNCATED_IMAGES = True

def optimize_image_size(image_path, max_size=(1600, 1600), quality=75):
    """
    ضغط صورة مع الحفاظ على النسبة الأصلية وجودة مقبولة
    """
    try:
        with Image.open(image_path) as img:
            # التحقق من أن الصورة صالحة
            img.verify()
        
        # إعادة فتح الصورة بعد التحقق
        with Image.open(image_path) as img:
            # تحويل إلى RGB إذا كانت الصورة من نوع RGBA أو P
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            
            # الحفاظ على النسبة الأصلية للصورة
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # حفظ الصورة المضغوطة
            compressed_path = image_path.replace('.jpg', '_compressed.jpg')
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
            
            # حفظ بإعدادات مضغوطة
            img.save(
                compressed_path, 
                'JPEG', 
                quality=quality, 
                optimize=True, 
                progressive=True
            )
            
            # التحقق من أن الملف المضغوط موجود وصالح
            if os.path.exists(compressed_path):
                with Image.open(compressed_path) as test_img:
                    test_img.verify()
                
                original_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
                compressed_size = os.path.getsize(compressed_path)
                
                if original_size > 0:
                    compression_ratio = (1 - compressed_size/original_size) * 100
                    logging.info(f"📏 ضغط الصورة: {original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB ({compression_ratio:.1f}%)")
                else:
                    logging.info(f"📏 ضغط الصورة: {compressed_size/1024:.1f}KB")
                
                return compressed_path
            
    except Exception as e:
        logging.error(f"❌ خطأ في ضغط الصورة {os.path.basename(image_path)}: {e}")
        # في حالة الخطأ، نعود للصورة الأصلية
        return image_path

def safe_image_conversion(image_path):
    """
    تحويل الصورة إلى تنسيق آمن لإنشاء PDF
    """
    try:
        temp_path = image_path + '_safe.jpg'
        
        with Image.open(image_path) as img:
            # تحويل جميع الصور إلى RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # حفظ كصورة JPEG آمنة
            img.save(temp_path, 'JPEG', quality=85, optimize=True)
            
        return temp_path
    except Exception as e:
        logging.error(f"❌ خطأ في تحويل الصورة {os.path.basename(image_path)}: {e}")
        return image_path

def create_compressed_pdf(image_paths, output_path):
    """
    إنشاء ملف PDF مضغوط من قائمة الصور
    """
    processed_paths = []
    temp_files = []
    
    try:
        # معالجة كل الصور أولاً
        for i, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                logging.warning(f"⚠️ الملف غير موجود: {image_path}")
                continue
                
            logging.info(f"🔧 معالجة الصورة {i+1}/{len(image_paths)}: {os.path.basename(image_path)}")
            
            try:
                # أولاً: ضغط الصورة
                compressed_path = optimize_image_size(image_path)
                if compressed_path != image_path:
                    temp_files.append(compressed_path)
                    final_path = compressed_path
                else:
                    final_path = image_path
                
                # ثانياً: تحويل الصورة إلى تنسيق آمن إذا لزم الأمر
                safe_path = safe_image_conversion(final_path)
                if safe_path != final_path:
                    temp_files.append(safe_path)
                    final_path = safe_path
                
                # التحقق النهائي من وجود الملف
                if os.path.exists(final_path):
                    # اختبار فتح الصورة
                    with Image.open(final_path) as test_img:
                        test_img.verify()
                    processed_paths.append(final_path)
                    logging.info(f"✅ تمت معالجة الصورة {i+1} بنجاح")
                else:
                    logging.error(f"❌ الملف النهائي غير موجود: {final_path}")
                    
            except Exception as e:
                logging.error(f"❌ فشل معالجة الصورة {image_path}: {e}")
                # حاول استخدام الصورة الأصلية كحل أخير
                if os.path.exists(image_path):
                    processed_paths.append(image_path)
                    logging.info(f"🔄 استخدام الصورة الأصلية للصورة {i+1}")
        
        if not processed_paths:
            raise Exception("لم تتم معالجة أي صور بنجاح")
        
        logging.info(f"📄 جاري إنشاء PDF من {len(processed_paths)} صورة...")
        
        # إعدادات PDF مبسطة - إصلاح الخطأ هنا
        try:
            # الطريقة المبسطة: استخدام حجم A4 ثابت
            a4_layout = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))  # A4 بالبوصة
            
            # إنشاء PDF مع إعدادات مبسطة
            with open(output_path, "wb") as f:
                pdf_data = img2pdf.convert(
                    processed_paths, 
                    layout_fun=lambda img: img2pdf.get_fixed_dpi_layout_fun((210, 297))(img)
                )
                f.write(pdf_data)
                
        except Exception as pdf_error:
            logging.error(f"❌ خطأ في الإعدادات المتقدمة للPDF: {pdf_error}")
            # الطريقة الأبسط: إنشاء PDF بدون إعدادات خاصة
            logging.info("🔄 جرب إنشاء PDF بالإعدادات الافتراضية...")
            with open(output_path, "wb") as f:
                pdf_data = img2pdf.convert(processed_paths)
                f.write(pdf_data)
        
        # التحقق من أن PDF تم إنشاؤه
        if not os.path.exists(output_path):
            raise Exception("فشل إنشاء ملف PDF")
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # بالميجابايت
        logging.info(f"✅ تم إنشاء PDF بنجاح! الحجم: {file_size:.2f} MB")
        
    except Exception as e:
        logging.error(f"❌ خطأ في إنشاء PDF: {e}")
        logging.error(traceback.format_exc())
        raise
    
    finally:
        # تنظيف الملفات المؤقتة
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file) and temp_file != output_path:
                    os.remove(temp_file)
            except Exception as e:
                logging.warning(f"⚠️ لا يمكن حذف الملف المؤقت {temp_file}: {e}")
