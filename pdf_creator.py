import img2pdf
from PIL import Image
import os
import logging

def compress_image(image_path, max_size=(1600, 1600), quality=65):
    """
    ضغط صورة مع الحفاظ على النسبة الأصلية
    """
    try:
        with Image.open(image_path) as img:
            # تحويل إلى RGB إذا كانت الصورة من نوع RGBA
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # الحفاظ على النسبة الأصلية للصورة
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # حفظ الصورة المضغوطة
            compressed_path = image_path.replace('.jpg', '_compressed.jpg')
            img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
            
            return compressed_path
    except Exception as e:
        logging.error(f"خطأ في ضغط الصورة {image_path}: {e}")
        return image_path

def create_compressed_pdf(image_paths, output_path):
    """
    إنشاء ملف PDF مضغوط من قائمة الصور
    """
    compressed_paths = []
    
    try:
        # ضغط كل الصور أولاً
        for i, image_path in enumerate(image_paths):
            logging.info(f"جاري ضغط الصورة {i+1}/{len(image_paths)}")
            compressed_path = compress_image(image_path)
            compressed_paths.append(compressed_path)
        
        # إنشاء PDF من الصور المضغوطة
        logging.info("جاري إنشاء PDF...")
        
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(compressed_paths))
        
        # تنظيف الملفات المضغوطة المؤقتة
        for compressed_path in compressed_paths:
            if compressed_path.endswith('_compressed.jpg'):
                try:
                    os.remove(compressed_path)
                except:
                    pass
        
        # الحصول على حجم الملف النهائي
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # بالميجابايت
        logging.info(f"تم إنشاء PDF بنجاح! الحجم: {file_size:.2f} MB")
        
    except Exception as e:
        logging.error(f"خطأ في إنشاء PDF: {e}")
        raise
