import requests
import os
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image
import io

def download_images(base_url, download_dir):
    """
    تحميل الصور من الموقع التي تبدأ بـ 001.jpg وتتزايد رقمياً
    """
    image_paths = []
    session = requests.Session()
    
    try:
        # جلب محتوى الصفحة للبحث عن الصور
        response = session.get(base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        img_tags = soup.find_all('img')
        
        # البحث عن الصور التي تطابق النمط
        found_images = []
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src:
                img_url = urljoin(base_url, src)
                found_images.append(img_url)
        
        # محاولة تحميل الصور بالتسلسل الرقمي
        counter = 1
        while True:
            # إنشاء اسم الملف المتوقع (001.jpg, 002.jpg, إلخ)
            filename = f"{counter:03d}.jpg"
            possible_urls = [
                urljoin(base_url, filename),
                urljoin(base_url, f"image/{filename}"),
                urljoin(base_url, f"images/{filename}"),
                urljoin(base_url, f"img/{filename}")
            ]
            
            # إضافة أي روابط موجودة في الصفحة تطابق النمط
            for found_url in found_images:
                if found_url.endswith(filename):
                    possible_urls.append(found_url)
            
            downloaded = False
            for img_url in possible_urls:
                try:
                    response = session.get(img_url, timeout=30)
                    if response.status_code == 200:
                        # التحقق مما إذا كان المحتوى صورة
                        if 'image' in response.headers.get('content-type', ''):
                            image_path = os.path.join(download_dir, filename)
                            with open(image_path, 'wb') as f:
                                f.write(response.content)
                            
                            # التحقق من أن الملف صورة صالحة
                            try:
                                with Image.open(image_path) as img:
                                    img.verify()
                                image_paths.append(image_path)
                                logging.info(f"تم تحميل: {img_url}")
                                downloaded = True
                                break
                            except Exception:
                                os.remove(image_path)
                                continue
                except Exception as e:
                    continue
            
            if not downloaded:
                # إذا لم نجد صورة لهذا الرقم، نتوقف
                if counter > 1:  # على الأقل وجدنا صورة واحدة
                    break
                else:
                    counter += 1
                    continue
            
            counter += 1
            
            # حد أقصى للسلامة - لا نريد تحميل آلاف الصور بالخطأ
            if counter > 500:
                break
                
    except Exception as e:
        logging.error(f"خطأ في تحميل الصور: {e}")
    
    return image_paths
