from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import cloudscraper, aiohttp, asyncio
from io import BytesIO
from PIL import Image
import img2pdf
import zipfile

app = FastAPI()
scraper = cloudscraper.create_scraper()

async def fetch_and_compress(session, url, quality):
    try:
        resp = await session.get(url)
        data = await resp.read()
        img = Image.open(BytesIO(data)).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return buf
    except Exception:
        return None

@app.get("/")
def root():
    return {"message": "✅ Manga Image Compressor Ready"}

@app.get("/compress")
async def compress(url: str, quality: int = 50):
    buf = await fetch_and_compress(scraper, url, quality)
    if not buf:
        raise HTTPException(status_code=500, detail="❌ Failed to fetch or compress image")
    return StreamingResponse(buf, media_type="image/jpeg")

@app.post("/batch")
async def batch(urls: list[str], quality: int = 50, to_pdf: bool = False):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_compress(session, u, quality) for u in urls]
        results = await asyncio.gather(*tasks)
    bufs = [b for b in results if b]
    if not bufs:
        raise HTTPException(500, "❌ No images fetched")

    if to_pdf:
        pdf = img2pdf.convert([b.getvalue() for b in bufs])
        return StreamingResponse(BytesIO(pdf), media_type="application/pdf")

    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, 'w') as z:
        for i, img in enumerate(bufs, 1):
            z.writestr(f"{i:03}.jpg", img.getvalue())
    zip_buf.seek(0)
    return StreamingResponse(zip_buf, media_type="application/zip")
