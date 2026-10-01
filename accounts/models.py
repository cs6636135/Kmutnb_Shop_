from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
     class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
     role = models.CharField(max_length=30, choices=Role.choices, default=Role.STAFF) #แอดมินเพิ่มสต๊าฟเข้าระบบ 
     location = models.ForeignKey("shop.Location",on_delete=models.SET_NULL, null=True, blank=True)
#ถ้าลบโลเคชั่นออก user staff จะยังคงอยู่ แต่ location จะเป็น null 
# choice .do_nothing คือ location ข้อมุลสถานที่ยังอยู่ในนี้
# หรือจะลบ location แล้วเอา staff หายไปเลย .cascade ??
# protect คือ ถ้ามี staff อยู่ใน location นั้น จะไม่สามารถลบ location ได้ ต้องเคลียร์ staff ก่อน ลบ เช่นลบ สต๊าฟ 100 คน?? จึงจะลบ location ได้

# Create your models here.