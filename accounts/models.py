from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class User(AbstractUser):
     class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
     phone = models.CharField(max_length=20, blank=True)
     role = models.CharField(max_length=30, choices=Role.choices, default=Role.STAFF) #แอดมินเพิ่มสต๊าฟเข้าระบบ 
     location = models.ForeignKey("shop.Location",on_delete=models.PROTECT, null=True, blank=True)

     def clean(self):                                          #Staff ต้องมีสถานที่
        super().clean()
        if self.role == self.Role.STAFF and not self.location_id:
            raise ValidationError({"location": "Staff ต้องมีสถานที่รับผิดชอบ"})
        if self.role == self.Role.ADMIN and self.location_id:
            raise ValidationError({"location": "Admin ไม่ผูกกับสถานที่"})


# Create your models here.