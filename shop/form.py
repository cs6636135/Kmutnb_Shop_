from django.forms import ModelForm 
from django.forms.widgets import TextInput
from .models import Product,Location,Category
from django.core.exceptions import ValidationError
from django import forms
from .storage import upload_image

class ImageUpload:
    image_folder = "products"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # สร้างช่องเลือกไฟล์ตอนสร้างฟอร์ม (ไม่ได้อยู่ใน model เลยต้องเพิ่มเอง)
        self.fields["image"] = forms.ImageField(
            required=False,
            label="รูปภาพ",
            error_messages={"invalid_image": "ไฟล์ต้องเป็นรูปภาพเท่านั้น"},
            widget=forms.FileInput(attrs={
                "accept": "image/*",
                "class": "block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[#30415D] file:px-4 file:py-2 file:text-white",
            }),
        )

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 10 * 1024 * 1024:
            raise ValidationError("รูปต้องมีขนาดไม่เกิน 10 MB")
        return image

    def save(self, commit=True):
        obj = super().save(commit=False)          # ยังไม่บันทึกลง DB
        image = self.cleaned_data.get("image")
        if image:
            try:
                path, url = upload_image(image, folder=self.image_folder)
            except Exception:
                raise ValidationError("อัปโหลดรูปไม่สำเร็จ กรุณาลองใหม่")
            obj.image_url = obj._meta.get_field("image_url").clean(url, obj) #ใช้ของโมเดลมาคลีน
        if commit:
            obj.save()
        return obj
    
class CleanName:
    # ลบอักขระล่องหน (\u200b, \ufeff) ที่ติดมาตอน copy/paste แล้วตัดช่องว่างหัวท้าย
    # เช่น "Iphone\u200b17" -> "Iphone17"   (\u200b = zero-width space)
    # "\ufeffIphone 17" -> "Iphone 17" (\ufeff = BOM)
    name_required_msg = "กรุณากรอกชื่อ"

    def clean_name(self):
        name = (self.cleaned_data["name"].replace("\u200b", "").replace("\ufeff", "").strip())
        if not name:
            raise ValidationError(self.name_required_msg)
        return name
    
INPUT = "w-full min-w-0 rounded-lg border border-slate-300 px-4 py-3 text-base outline-none focus:border-[#F47745] focus:ring-2 focus:ring-[#F47745]/20"
SELECT = INPUT + " bg-white"


class ProductModelForm(ImageUpload, CleanName, ModelForm):
    name_required_msg = "กรุณากรอกชื่อสินค้า"
    image_folder = "products"

    class Meta:
        model = Product
        fields = ["name", "description", "price", "category", "reservable"]
        labels = {
            "name": "ชื่อสินค้า",
            "description": "รายละเอียดสินค้า",
            "price": "ราคา (บาท)",
            "reservable": "สามารถจองสินค้าได้หรือไม่",
            "category": "หมวดหมู่สินค้า",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "ชื่อสินค้า"}),
            "description": forms.Textarea(attrs={"class": INPUT, "placeholder": "รายละเอียดสินค้า", "rows": 4}),
            "price": forms.NumberInput(attrs={"class": INPUT, "min": "0", "step": "0.01", "placeholder": "0.00"}),
            "reservable": forms.RadioSelect(),
            "category": forms.Select(attrs={"class": SELECT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "กรุณาเลือกหมวดหมู่สินค้า"


class LocationModelForm(ImageUpload, CleanName, ModelForm):
    name_required_msg = "กรุณากรอกชื่อจุดจำหน่าย"
    image_folder = "locations"

    class Meta:
        model = Location
        fields = ["name", "building", "floor", "room", "description"]
        labels = {
            "name": "ชื่อจุดจำหน่าย",
            "building": "ตึก",
            "floor": "ชั้น",
            "room": "ห้อง",
            "description": "รายละเอียดจุดจำหน่าย",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "ชื่อจุดจำหน่าย"}),
            "building": forms.TextInput(attrs={"class": INPUT, "placeholder": "ชื่อตึก"}),
            "floor": forms.TextInput(attrs={"class": INPUT, "placeholder": "ชั้น"}),
            "room": forms.TextInput(attrs={"class": INPUT, "placeholder": "ห้อง"}),
            "description": forms.Textarea(attrs={"class": INPUT, "placeholder": "รายละเอียดจุดจำหน่าย", "rows": 4}),
        }

class CategoryModelForm(ModelForm,CleanName):
    name_required_msg = "กรุณากรอกชื่อหมวดหมู่สินค้า"

    class Meta:
        model = Category
        fields = ["name", "description"]
        labels = {
            "name": "ชื่อหมวดหมู่สินค้า",
            "description": "รายละเอียด",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "ชื่อหมวดหมู่สินค้า"}),
            "description": forms.Textarea(attrs={"class": INPUT, "placeholder": "รายละเอียดหมวดหมู่สินค้า", "rows": 4}),
        }
