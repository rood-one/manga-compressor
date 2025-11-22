import img2pdf
from PIL import Image
import os
import logging

def optimize_image_size(image_path, max_size=(1200, 1200), quality=60):
    """
    ضغط صورة مع الحفاظ على النسبة الأصلية وجودة مقبولة
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
            img.save(compressed_path, 'JPEG', quality=quality, optimize=True, progressive=True)
            
            original_size = os.path.getsize(image_path)
            compressed_size = os.path.getsize(compressed_path)
            compression_ratio = (1 - compressed_size/original_size) * 100
            
            logging.info(f"📏 ضغط الصورة: {original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB ({compression_ratio:.1f}%)")
            
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
            logging.info(f"🔧 جاري ضغط الصورة {i+1}/{len(image_paths)}")
            compressed_path = optimize_image_size(image_path)
            compressed_paths.append(compressed_path)
        
        # إنشاء PDF من الصور المضغوطة
        logging.info("📄 جاري إنشاء PDF...")
        
        # إعدادات PDF لتحسين الحجم
        pdf_layout = img2pdf.get_layout_fun(
            pagesize=img2pdf.get_fit_size(
                img2pdf.mm_to_pt((210, 297)),  # A4
                img2pdf.mm_to_pt((160, 240))   # حدود أصغر
            )
        )
        
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(compressed_paths, layout_fun=pdf_layout))
        
        # تنظيف الملفات المضغوطة المؤقتة
        for compressed_path in compressed_paths:
            if compressed_path.endswith('_compressed.jpg'):
                try:
                    os.remove(compressed_path)
                except:
                    pass
        
        # الحصول على حجم الملف النهائي
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # بالميجابايت
        logging.info(f"✅ تم إنشاء PDF بنجاح! الحجم: {file_size:.2f} MB")
        
    except Exception as e:
        logging.error(f"❌ خطأ في إنشاء PDF: {e}")
        raise
