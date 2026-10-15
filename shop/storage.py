import io
import uuid
from django.conf import settings
from PIL import Image, ImageOps
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
BUCKET = "img"


def shrink_image(file, max_side=1200):
    # เปิดรูป แล้วหมุนให้ตรงตามที่ถ่ายมา (รูปจากมือถือมักตะแคง)
    img = ImageOps.exif_transpose(Image.open(file))
    img = img.convert("RGB") #กันภาพโปร่งแสงจาก webp  ละ error
    # ย่อให้ด้านยาวสุดไม่เกิน 1200 พิกเซล รักษาสัดส่วนเดิม
    img.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def upload_image(file, folder="products"):
    data = shrink_image(file)
    path = f"{folder}/{uuid.uuid4().hex}.jpg"   # ย่อแล้วเป็น jpg เสมอ
    #ใช้ uuid เพราะสร้างชื่อไม่ซ้ำได้ทันทีโดยไม่ต้องตรวจสอบกับฐานข้อมูล 
    supabase.storage.from_(BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": "image/jpeg"},
    )
    return supabase.storage.from_(BUCKET).get_public_url(path)