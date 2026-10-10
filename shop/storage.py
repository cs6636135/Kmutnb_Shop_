import io
import os
import uuid
from django.conf import settings
from PIL import Image, ImageOps
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
BUCKET = "img"


def shrink_image(file, max_side=1200):
    # เปิดรูป แล้วหมุนให้ตรงตามที่ถ่ายมา (รูปจากมือถือมักตะแคง)
    img = ImageOps.exif_transpose(Image.open(file))
    img = img.convert("RGB")
    # ย่อให้ด้านยาวสุดไม่เกิน 1200 พิกเซล รักษาสัดส่วนเดิม
    img.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def upload_image(file, folder="products"):
    # เช็คว่าเป็นรูป และไม่ใหญ่เกินไปจนเปิดไม่ไหว (ย่อทีหลังได้ ไม่ต้องจำกัดแค่ 2 MB แล้ว)
    if not file.content_type.startswith("image/"):
        raise ValueError("ไฟล์ต้องเป็นรูปภาพเท่านั้น")
    if file.size > 10 * 1024 * 1024:
        raise ValueError("รูปต้องมีขนาดไม่เกิน 10 MB")

    data = shrink_image(file)
    path = f"{folder}/{uuid.uuid4().hex}.jpg"   # ย่อแล้วเป็น jpg เสมอ

    supabase.storage.from_(BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": "image/jpeg"},
    )
    return path, supabase.storage.from_(BUCKET).get_public_url(path)