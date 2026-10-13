from django.forms import ModelForm 
from .models import Product,Location,Category,ProductLocation
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
                 url = upload_image(image, folder=self.image_folder)
            except Exception:
                raise ValidationError("อัปโหลดรูปไม่สำเร็จ กรุณาลองใหม่")
            obj.image_url = obj._meta.get_field("image_url").clean(url, obj) #ใช้ของโมเดลมาคลีน
        if commit:
            obj.save()
        return obj
    
INPUT = "w-full min-w-0 rounded-lg border border-slate-300 px-4 py-3 text-base outline-none focus:border-[#F47745] focus:ring-2 focus:ring-[#F47745]/20"
SELECT = INPUT + " bg-white"


class ProductModelForm(ImageUpload, ModelForm):
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
        error_messages = {
            "name": {
                "required": "กรุณากรอกชื่อสินค้า",
                "unique": "มีสินค้าชื่อนี้อยู่แล้ว",
                "max_length": "ชื่อสินค้ายาวเกินไป (ไม่เกิน 150 ตัวอักษร)",
            },
            "price": {
                "required": "กรุณากรอกราคา",
                "invalid": "กรุณากรอกราคาเป็นตัวเลข",
                "min_value": "ราคาต้องไม่ติดลบ",
                "max_digits": "ราคาต้องมีตัวเลขไม่เกิน 10 หลัก",
                "max_decimal_places": "ราคาทศนิยมได้ไม่เกิน 2 ตำแหน่ง",
                "max_whole_digits": "ราคาสูงเกินไป",
            },
            "category": {
                "required": "กรุณาเลือกหมวดหมู่สินค้า",
                "invalid_choice": "หมวดหมู่ที่เลือกไม่ถูกต้อง",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "กรุณาเลือกหมวดหมู่สินค้า"

class ProductLocationForm(ModelForm):
    class Meta:
        model = ProductLocation
        fields = ["product","location", "stock"]
        labels = {
            "product": "สินค้า",
            "location": "จุดจำหน่าย",
            "stock": "จำนวนสินค้า",
        }
        widgets = {
            "product": forms.Select(attrs={"class": SELECT}),
            "location": forms.Select(attrs={"class": SELECT}),
            "stock": forms.NumberInput(attrs={"class": INPUT, "min": "0", "step": "1", "placeholder": "0"}),
        }
        error_messages = {
            "product": {
                "required": "กรุณาเลือกสินค้า",
                "invalid_choice": "สินค้าที่เลือกไม่ถูกต้อง",
            },
            "location": {
                "required": "กรุณาเลือกจุดจำหน่าย",
                "invalid_choice": "จุดจำหน่ายที่เลือกไม่ถูกต้อง",
            },
            "stock": {
                "required": "กรุณากรอกจำนวนสินค้า",
                "invalid": "กรุณากรอกจำนวนสินค้าเป็นตัวเลข",
                "min_value": "จำนวนสินค้าต้องเป็นจำนวนเต็มที่ไม่ติดลบ",
            },
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].empty_label = "กรุณาเลือกสินค้า"
        self.fields["location"].empty_label = "กรุณาเลือกจุดจำหน่าย"

        if user and user.role == "staff":
            if not user.location_id:
                raise ValidationError("คุณไม่มีสิทธิ์เข้าถึงฟังก์ชันนี้")
            self.fields["location"].queryset = Location.objects.filter(
                pk=user.location_id
            )
            self.fields["location"].initial = user.location_id
            self.fields["location"].disabled = True

class LocationModelForm(ImageUpload, ModelForm):
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
        error_messages = {
            "name": {
                "required": "กรุณากรอกชื่อจุดจำหน่าย",
                "max_length": "ชื่อจุดจำหน่ายยาวเกินไป (ไม่เกิน 150 ตัวอักษร)",
            },
            "building": {
                "required": "กรุณากรอกชื่อตึก",
                "max_length": "ชื่อตึกยาวเกินไป (ไม่เกิน 100 ตัวอักษร)",
            },
            "floor": {
                "max_length": "ชั้นยาวเกินไป (ไม่เกิน 30 ตัวอักษร)",
            },
            "room": {
                "max_length": "ชื่อห้องยาวเกินไป (ไม่เกิน 100 ตัวอักษร)",
            },
        }

class CategoryModelForm(ModelForm):

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
        error_messages = {
            "name": {
                "required": "กรุณากรอกชื่อหมวดหมู่สินค้า",
                "unique": "มีหมวดหมู่สินค้าชื่อนี้อยู่แล้ว",
                "max_length": "ชื่อหมวดหมู่ยาวเกินไป (ไม่เกิน 100 ตัวอักษร)",
            },
        }
