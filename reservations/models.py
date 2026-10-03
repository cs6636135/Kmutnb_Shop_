from django.db import models
# Create your models here.

class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PICKED_UP = "picked_up", "Picked up"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    reservation_code = models.CharField(max_length=30, unique=True,editable=False)
    customer_id = models.CharField(max_length=20)  # รหัสลูกค้า ไม่ใช่ FK
    product = models.ForeignKey("shop.Product", on_delete=models.PROTECT) #กันไว้ตอนลบสินค้าที่มีการจองค้าง
    location = models.ForeignKey("shop.Location", on_delete=models.PROTECT) #กันไว้ตอนลบสถานที่มีการจองค้าง แอดมินไปแคนเซิลการจองแทน
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(editable=False)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)