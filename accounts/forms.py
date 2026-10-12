from django import forms
from django.forms import ModelForm 
from .models import User

INPUT = "w-full min-w-0 rounded-lg border border-slate-300 px-4 py-3 text-base outline-none focus:border-[#F47745] focus:ring-2 focus:ring-[#F47745]/20"
SELECT = INPUT + " bg-white"

class UserModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "location" in self.fields:
            self.fields["location"].empty_label = "-- เลือกจุดจำหน่าย --"
        # หากเป็นการแก้ไขบัญชีเดิม ไม่บังคับให้ต้องเปลี่ยนรหัสผ่าน
        if self.instance and self.instance.pk:
            self.fields["password"].required = False
            self.fields["password"].help_text = "เว้นว่างไว้หากไม่ต้องการเปลี่ยนรหัสผ่าน"

    # password = forms.CharField(
    #     required=False,
    #     widget=forms.PasswordInput(attrs={"class": INPUT, "placeholder": "รหัสผ่าน"}),
    #     label="รหัสผ่าน"
    #     )

    def clean_username(self):
        username = self.cleaned_data["username"].replace("\u200b", "").replace("\ufeff", "").strip()
        if not username:
            raise forms.ValidationError("กรุณากรอกชื่อผู้ใช้")
        return username

    def save(self, commit=True):
        old_password = None

        #เช็คว่าใช่การแก้ไขไหม ถ้าใช่เก็บ old password ไว้
        if self.instance and self.instance.pk:
            old_password = User.objects.get(pk=self.instance.pk).password
            
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        #ถ้ามีการ input password ให้แก้ไข password เป็นอันใหม่
        if password:
            user.set_password(password)
        #ถ้าไม่มีการ input password ให้ใช้ old password
        else:
            user.password = old_password
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ["username", "password", "first_name", "last_name", "phone", "location", "role"]
        labels = {
            "username": "ชื่อผู้ใช้",
            "password": "รหัสผ่าน",
            "first_name": "ชื่อ",
            "last_name": "นามสกุล",
            "phone": "เบอร์โทรศัพท์",
            "location": "จุดจำหน่าย",
            "role": "บทบาท",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT, "placeholder": "ชื่อผู้ใช้"}),
            "password": forms.PasswordInput(attrs={"class": INPUT, "placeholder": "รหัสผ่าน"}),
            "first_name": forms.TextInput(attrs={"class": INPUT, "placeholder": "ชื่อ"}),
            "last_name": forms.TextInput(attrs={"class": INPUT, "placeholder": "นามสกุล"}),
            "phone": forms.TextInput(attrs={"class": INPUT, "placeholder": "เบอร์โทรศัพท์"}),
            "location": forms.Select(attrs={"class": SELECT}),
            "role": forms.Select(attrs={"class": SELECT}),
        }
        error_messages = {
            "username": {
                "required": "กรุณากรอกชื่อผู้ใช้",
                "unique": "มีชื่อผู้ใช้นี้อยู่แล้ว",
                "max_length": "ชื่อผู้ใช้ยาวเกินไป (ไม่เกิน 150 ตัวอักษร)",
            },
            "password": {
                "required": "กรุณากรอกรหัสผ่าน",
                "max_length": "รหัสผ่านยาวเกินไป (ไม่เกิน 150 ตัวอักษร)",
            },
            "first_name": {
                "required": "กรุณากรอกชื่อ",
                "max_length": "ชื่อยาวเกินไป (ไม่เกิน 150 ตัวอักษร)",
            },
            "last_name": {
                "required": "กรุณากรอกนามสกุล",
                "max_length": "นามสกุลยาวเกินไป (ไม่เกิน 150 ตัวอักษร)",
            },
            "phone": {
                "required": "กรุณากรอกเบอร์โทรศัพท์",
                "max_length": "เบอร์โทรศัพท์ยาวเกินไป (ไม่เกิน 15 ตัวอักษร)",
            },
            "location": {
                "required": "กรุณาเลือกจุดจำหน่าย",
                "invalid_choice": "จุดจำหน่ายที่เลือกไม่ถูกต้อง",
            },
            "role": {
                "required": "กรุณาเลือกบทบาท",
                "invalid_choice": "บทบาทที่เลือกไม่ถูกต้อง",
            },
        }