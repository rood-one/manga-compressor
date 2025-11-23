import img2pdf
from PIL import Image, ImageFile
import os
import logging

ImageFile.LOAD_TRUNCATED_IMAGES = True

def create_high_quality_pdf(image_paths, output_path):
    """
    إنشاء PDF بجودة عالية مع الحد الأدنى من الضغط
    """
    valid_images = []
    
    try:
        # معالجة الصور مع الحفاظ على الجودة
        for i, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                continue
                
            try:
                with Image.open(image_path) as img:
                    original_width, original_height = img.size
                    logging.info(f"📐 معالجة الصورة {i+1}: {original_width}x{original_height}")
                    
                    # تحويل إلى RGB إذا لزم الأمر
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # للصور الطويلة: تقليل العرض فقط مع الحفاظ على الطول
                    if original_height > 2000:
                        # حساب العرض الجديد مع الحفاظ على النسبة
                        new_width = min(1000, original_width)  # أقصى عرض 1000 بكسل
                        new_height = int((original_height * new_width) / original_width)
                        
                        # إعادة التحجيم بخوارزمية عالية الجودة
                        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        logging.info(f"📏 الصورة الطويلة - الأبعاد الجديدة: {new_width}x{new_height}")
                    else:
                        img_resized = img
                    
                    # حفظ بصيغة JPEG بجودة عالية
                    temp_path = image_path + '_hq.jpg'
                    
                    # جودة عالية للصور الطويلة
                    quality = 75 if original_height > 3000 else 90
                    
                    img_resized.save(temp_path, 'JPEG', quality=quality, optimize=True)
                    valid_images.append(temp_path)
                    
            except Exception as e:
                logging.error(f"❌ خطأ في معالجة {image_path}: {e}")
                continue
        
        if not valid_images:
            raise Exception("لا توجد صور صالحة للتحويل")
        
        # إنشاء PDF
        logging.info(f"📄 جاري إنشاء PDF عالي الجودة من {len(valid_images)} صورة...")
        
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(valid_images))
        
        # تنظيف الملفات المؤقتة
        for temp_image in valid_images:
            try:
                os.remove(temp_image)
            except:
                pass
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logging.info(f"✅ تم إنشاء PDF عالي الجودة! الحجم: {file_size:.2f} MB")
        
    except Exception as e:
        logging.error(f"❌ خطأ في إنشاء PDF عالي الجودة: {e}")
        raise
