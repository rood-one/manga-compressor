import img2pdf
from PIL import Image, ImageFile
import os
import logging
import traceback

# السماح بتحميل الصور التالفة جزئياً
ImageFile.LOAD_TRUNCATED_IMAGES = True

def optimize_image_size(image_path, max_width=1200, quality=65):
    """
    ضغط صورة مع الحفاظ على الجودة خاصة للصور الطويلة
    """
    try:
        with Image.open(image_path) as img:
            # التحقق من أن الصورة صالحة
            img.verify()
        
        # إعادة فتح الصورة بعد التحقق
        with Image.open(image_path) as img:
            original_width, original_height = img.size
            logging.info(f"📐 أبعاد الصورة الأصلية: {original_width}x{original_height}")
            
            # تحويل إلى RGB إذا كانت الصورة من نوع RGBA أو P
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            
            # للصور الطويلة: نحافظ على الطول ونضبط العرض فقط
            if original_height > 3000:  # إذا كانت الصورة طويلة
                # حساب العرض الجديد مع الحفاظ على النسبة
                if original_width > max_width:
                    new_width = max_width
                    new_height = int((original_height * max_width) / original_width)
                else:
                    new_width = original_width
                    new_height = original_height
                
                logging.info(f"📏 الصورة الطويلة - الأبعاد الجديدة: {new_width}x{new_height}")
                
                # إعادة التحجيم باستخدام خوارزمية عالية الجودة
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                # للصور العادية: استخدام thumbnail
                img.thumbnail((max_width, 3000), Image.Resampling.LANCZOS)
                resized_img = img
                logging.info(f"📏 الصورة العادية - الأبعاد الجديدة: {resized_img.size}")
            
            # حفظ الصورة المضغوطة
            compressed_path = image_path.replace('.jpg', '_compressed.jpg')
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
            
            # حفظ بإعدادات جودة أعلى للصور الطويلة
            save_quality = quality
            if original_height > 5000:
                save_quality = 60  # جودة أعلى للصور الطويلة جداً
            
            resized_img.save(
                compressed_path, 
                'JPEG', 
                quality=save_quality, 
                optimize=True, 
                progressive=False  # إيقاف progressive للصور الطويلة
            )
            
            # التحقق من أن الملف المضغوط موجود وصالح
            if os.path.exists(compressed_path):
                with Image.open(compressed_path) as test_img:
                    test_img.verify()
                    compressed_size = test_img.size
                    logging.info(f"✅ الأبعاد بعد الضغط: {compressed_size}")
                
                original_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
                compressed_size_bytes = os.path.getsize(compressed_path)
                
                if original_size > 0:
                    compression_ratio = (1 - compressed_size_bytes/original_size) * 100
                    logging.info(f"📊 ضغط الصورة: {original_size/1024:.1f}KB → {compressed_size_bytes/1024:.1f}KB ({compression_ratio:.1f}%)")
                else:
                    logging.info(f"📊 حجم الصورة المضغوطة: {compressed_size_bytes/1024:.1f}KB")
                
                return compressed_path
            
    except Exception as e:
        logging.error(f"❌ خطأ في ضغط الصورة {os.path.basename(image_path)}: {e}")
        logging.error(traceback.format_exc())
        # في حالة الخطأ، نعود للصورة الأصلية
        return image_path

def safe_image_conversion(image_path):
    """
    تحويل الصورة إلى تنسيق آمن لإنشاء PDF مع الحفاظ على الجودة
    """
    try:
        temp_path = image_path + '_safe.jpg'
        
        with Image.open(image_path) as img:
            original_width, original_height = img.size
            
            # تحويل جميع الصور إلى RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # جودة أعلى للصور الطويلة
            save_quality = 65
            if original_height > 5000:
                save_quality = 60
            elif original_height > 3000:
                save_quality = 68
            
            # حفظ كصورة JPEG آمنة
            img.save(temp_path, 'JPEG', quality=save_quality, optimize=True)
            
        return temp_path
    except Exception as e:
        logging.error(f"❌ خطأ في تحويل الصورة {os.path.basename(image_path)}: {e}")
        return image_path

def create_compressed_pdf(image_paths, output_path):
    """
    إنشاء ملف PDF مضغوط مع الحفاظ على جودة الصور الطويلة
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
                # أولاً: ضغط الصورة مع الحفاظ على الجودة
                compressed_path = optimize_image_size(image_path)
                if compressed_path != image_path:
                    temp_files.append(compressed_path)
                    final_path = compressed_path
                else:
                    final_path = image_path
                
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
        
        # إعدادات PDF محسنة للصور الطويلة
        try:
            # استخدام حجم الصفحة الذي يتناسب مع الصور الطويلة
            with open(output_path, "wb") as f:
                pdf_data = img2pdf.convert(
                    processed_paths,
                    # إعدادات متقدمة للجودة
                    rotation=img2pdf.Rotation.ifvalid
                )
                f.write(pdf_data)
                
        except Exception as pdf_error:
            logging.error(f"❌ خطأ في إنشاء PDF: {pdf_error}")
            # الطريقة البسيطة
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
