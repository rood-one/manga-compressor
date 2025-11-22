import img2pdf
from PIL import Image, ImageFile
import os
import logging

# السماح بتحميل الصور التالفة جزئياً
ImageFile.LOAD_TRUNCATED_IMAGES = True

def create_simple_pdf(image_paths, output_path):
    """
    إنشاء PDF بطريقة مبسطة وموثوقة
    """
    valid_images = []
    
    try:
        # التحقق من جميع الصور أولاً
        for image_path in image_paths:
            if not os.path.exists(image_path):
                continue
                
            try:
                with Image.open(image_path) as img:
                    # تحويل إلى RGB إذا لزم الأمر
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # حفظ نسخة مؤقتة بصيغة JPEG
                    temp_path = image_path + '_temp.jpg'
                    img.save(temp_path, 'JPEG', quality=80, optimize=True)
                    valid_images.append(temp_path)
                    
            except Exception as e:
                logging.error(f"❌ خطأ في معالجة {image_path}: {e}")
                continue
        
        if not valid_images:
            raise Exception("لا توجد صور صالحة للتحويل")
        
        # إنشاء PDF بطريقة مباشرة
        logging.info(f"📄 جاري إنشاء PDF من {len(valid_images)} صورة...")
        
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(valid_images))
        
        # تنظيف الملفات المؤقتة
        for temp_image in valid_images:
            try:
                os.remove(temp_image)
            except:
                pass
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logging.info(f"✅ تم إنشاء PDF بنجاح! الحجم: {file_size:.2f} MB")
        
    except Exception as e:
        logging.error(f"❌ خطأ في إنشاء PDF: {e}")
        raise
