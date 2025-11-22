import requests
import os
import logging
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image
import re

def wait_for_page_load(url, session, delay=5):
    """انتظار تحميل الصفحة بشكل كامل"""
    try:
        response = session.get(url)
        response.raise_for_status()
        logging.info(f"تم تحميل الصفحة بنجاح، الانتظار {delay} ثواني لتحميل الصور...")
        time.sleep(delay)  # انتظار لتحميل الصور
        return response.content
    except Exception as e:
        logging.error(f"خطأ في تحميل الصفحة: {e}")
        return None

def find_image_urls(soup, base_url):
    """الباحث عن جميع روابط الصور في الصفحة"""
    image_urls = []
    
    # البحث في وسوم img
    for img in soup.find_all('img'):
        for attr in ['src', 'data-src', 'data-original', 'data-source']:
            src = img.get(attr)
            if src:
                full_url = urljoin(base_url, src)
                if is_image_url(full_url):
                    image_urls.append(full_url)
    
    # البحث في وسوم a (لروابط مباشرة للصور)
    for link in soup.find_all('a', href=True):
        href = link['href']
        if is_image_url(href):
            full_url = urljoin(base_url, href)
            image_urls.append(full_url)
    
    # البحث في CSS background images
    for tag in soup.find_all(style=True):
        style = tag['style']
        urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
        for url in urls:
            full_url = urljoin(base_url, url)
            if is_image_url(full_url):
                image_urls.append(full_url)
    
    return list(set(image_urls))  # إزالة التكرارات

def is_image_url(url):
    """التحقق مما إذا كان الرابط يشير إلى صورة"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return any(url.lower().endswith(ext) for ext in image_extensions)

def download_sequential_images(base_url, download_dir, session, max_images=100):
    """تحميل الصور بالتسلسل الرقمي (001.jpg, 002.jpg, إلخ)"""
    downloaded_images = []
    
    for i in range(1, max_images + 1):
        # تنسيقات مختلفة للأسماء
        filenames = [
            f"{i:03d}.jpg",
            f"{i:03d}.jpeg", 
            f"{i:03d}.png",
            f"{i}.jpg",
            f"{i}.jpeg",
            f"image_{i:03d}.jpg",
            f"img_{i:03d}.jpg",
            f"page_{i:03d}.jpg"
        ]
        
        for filename in filenames:
            image_url = urljoin(base_url, filename)
            try:
                response = session.get(image_url, timeout=10)
                if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                    image_path = os.path.join(download_dir, f"{i:03d}.jpg")
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    # التحقق من أن الملف صورة صالحة
                    try:
                        with Image.open(image_path) as img:
                            img.verify()
                        downloaded_images.append(image_path)
                        logging.info(f"✅ تم تحميل: {image_url}")
                        break  # الانتقال للصورة التالية
                    except Exception:
                        os.remove(image_path)  # حذف الملف غير الصالح
                        continue
                        
            except Exception as e:
                continue
    
    return downloaded_images

def download_images(base_url, download_dir):
    """الدالة الرئيسية لتحميل الصور"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    all_downloaded = []
    
    try:
        # الانتظار لتحميل الصفحة
        page_content = wait_for_page_load(base_url, session, delay=7)
        if not page_content:
            return []
        
        # البحث عن الصور في الصفحة
        soup = BeautifulSoup(page_content, 'html.parser')
        found_urls = find_image_urls(soup, base_url)
        
        logging.info(f"🔍 تم العثور على {len(found_urls)} رابط صورة محتمل في الصفحة")
        
        # تحميل الصور التي تم العثور عليها
        for i, img_url in enumerate(found_urls):
            try:
                response = session.get(img_url, timeout=15)
                if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                    filename = f"found_{i+1:03d}.jpg"
                    image_path = os.path.join(download_dir, filename)
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    # التحقق من الصورة
                    try:
                        with Image.open(image_path) as img:
                            img.verify()
                        all_downloaded.append(image_path)
                        logging.info(f"✅ تم تحميل صورة من الصفحة: {os.path.basename(img_url)}")
                    except Exception:
                        os.remove(image_path)
                        
            except Exception as e:
                logging.warning(f"⚠️ فشل تحميل صورة من الصفحة: {img_url}")
        
        # إذا لم نجد صوراً من خلال تحليل الصفحة، نجرب الطريقة الرقمية
        if not all_downloaded:
            logging.info("🔄 جرب البحث عن الصور بالتسلسل الرقمي...")
            sequential_images = download_sequential_images(base_url, download_dir, session)
            all_downloaded.extend(sequential_images)
        
        # ترتيب الصور حسب الأسماء
        all_downloaded.sort()
        
    except Exception as e:
        logging.error(f"❌ خطأ في عملية التحميل: {e}")
    
    logging.info(f"📊 إجمالي الصور التي تم تحميلها: {len(all_downloaded)}")
    return all_downloaded
