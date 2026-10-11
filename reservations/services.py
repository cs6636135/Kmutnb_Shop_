from django.db import transaction
from django.utils import timezone

from shop.models import ProductLocation
from .models import Reservation


from django.db import transaction
from django.utils import timezone

from shop.models import ProductLocation
from .models import Reservation


def expire_overdue_reservations(product_id=None):
    """เปลี่ยนรายการจองที่หมดเวลาเป็น expired และคืนสต็อก"""
    now = timezone.now()
    expired_count = 0

    # atomic: คืนสต็อกกับเปลี่ยนสถานะ ต้องสำเร็จพร้อมกันหรือย้อนกลับพร้อมกัน
    with transaction.atomic():
        # หาการจองที่ยัง pending และหมดเวลาแล้ว (ล็อกไว้กันประมวลผลซ้ำ)
        overdue = Reservation.objects.select_for_update().filter(
            status=Reservation.Status.PENDING,
            expires_at__lte=now,
        )
        if product_id is not None:
            overdue = overdue.filter(product_id=product_id)

        for r in overdue:
            # หาแถวสต็อกของสินค้านี้ ณ จุดที่จอง (ล็อกไว้กันค่าถูกทับ)
            pl = ProductLocation.objects.select_for_update().get(
                product_id=r.product_id,
                location_id=r.location_id,
            )
            pl.stock = pl.stock + r.quantity   # คืนสต็อก
            pl.save()

            r.status = Reservation.Status.EXPIRED
            r.save()
            expired_count += 1

    return expired_count
