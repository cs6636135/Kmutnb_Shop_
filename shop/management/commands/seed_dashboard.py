from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.apps import apps

from shop.models import Product, Location


class Command(BaseCommand):
    help = "สร้างข้อมูล Reservation สำหรับทดสอบหน้า Dashboard"

    # ============================================================
    # สินค้าที่จะนำมาสร้าง Reservation
    # เน้นหนังสือเป็นหลัก
    # ============================================================
    RESERVATIONS = [
        {
            "code": "RES-DASH-001",
            "customer_id": "66010001",
            "product": "คณิตศาสตร์วิศวกรรม 1",
            "location": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
            "quantity": 1,
            "status": "pending",
            "expires_minutes": 120,
        },
        {
            "code": "RES-DASH-002",
            "customer_id": "66010002",
            "product": "ฟิสิกส์วิศวกรรม 1",
            "location": "ร้านสวัสดิการ โรงอาหารกลาง",
            "quantity": 1,
            "status": "pending",
            "expires_minutes": 180,
        },
        {
            "code": "RES-DASH-003",
            "customer_id": "66010003",
            "product": "การเขียนโปรแกรมคอมพิวเตอร์",
            "location": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
            "quantity": 2,
            "status": "pending",
            "expires_minutes": 240,
        },
        {
            "code": "RES-DASH-004",
            "customer_id": "66010004",
            "product": "กลศาสตร์วัสดุ",
            "location": "ร้านสวัสดิการ โรงอาหารกลาง",
            "quantity": 1,
            "status": "pending",
            "expires_minutes": 300,
        },
        {
            "code": "RES-DASH-005",
            "customer_id": "66010005",
            "product": "สถิติสำหรับวิศวกร",
            "location": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
            "quantity": 1,
            "status": "pending",
            "expires_minutes": 30,
        },

        # --------------------------------------------------------
        # Picked Up
        # --------------------------------------------------------
        {
            "code": "RES-DASH-006",
            "customer_id": "65010001",
            "product": "คณิตศาสตร์วิศวกรรม 2",
            "location": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
            "quantity": 1,
            "status": "picked_up",
            "expires_minutes": -2880,
        },
        {
            "code": "RES-DASH-007",
            "customer_id": "65010002",
            "product": "ฐานข้อมูลเบื้องต้น",
            "location": "ร้านสวัสดิการ โรงอาหารกลาง",
            "quantity": 1,
            "status": "picked_up",
            "expires_minutes": -4320,
        },
        {
            "code": "RES-DASH-008",
            "customer_id": "65010003",
            "product": "เสื้อโปโล",
            "location": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
            "quantity": 1,
            "status": "picked_up",
            "expires_minutes": -5760,
        },

        # --------------------------------------------------------
        # Expired
        # --------------------------------------------------------
        {
            "code": "RES-DASH-009",
            "customer_id": "64010001",
            "product": "เคมีสำหรับวิศวกร",
            "location": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
            "quantity": 1,
            "status": "expired",
            "expires_minutes": -1440,
        },
        {
            "code": "RES-DASH-010",
            "customer_id": "64010002",
            "product": "ระบบปฏิบัติการ",
            "location": "ร้านสวัสดิการ โรงอาหารกลาง",
            "quantity": 1,
            "status": "expired",
            "expires_minutes": -2880,
        },

        # --------------------------------------------------------
        # Cancelled
        # --------------------------------------------------------
        {
            "code": "RES-DASH-011",
            "customer_id": "63010001",
            "product": "วัสดุวิศวกรรม",
            "location": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
            "quantity": 1,
            "status": "cancelled",
            "expires_minutes": -4320,
        },
        {
            "code": "RES-DASH-012",
            "customer_id": "63010002",
            "product": "กระเป๋าเป้",
            "location": "ร้านสวัสดิการ โรงอาหารกลาง",
            "quantity": 1,
            "status": "cancelled",
            "expires_minutes": -5760,
        },
    ]

    def handle(self, *args, **options):

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("=== เริ่มสร้างข้อมูล Dashboard ===")
        )
        self.stdout.write("")

        # ========================================================
        # 1. หา Reservation Model
        # ========================================================
        Reservation = None

        for model in apps.get_models():
            if model.__name__ == "Reservation":
                Reservation = model
                break

        if Reservation is None:
            raise CommandError(
                "ไม่พบ Reservation model ในโปรเจกต์"
            )

        # ========================================================
        # 2. ตรวจสอบ Product
        # ========================================================
        product_names = {
            item["product"]
            for item in self.RESERVATIONS
        }

        products = {
            product.name: product
            for product in Product.objects.filter(
                name__in=product_names
            )
        }

        missing_products = [
            name
            for name in product_names
            if name not in products
        ]

        if missing_products:
            raise CommandError(
                "ไม่พบสินค้าต่อไปนี้:\n- "
                + "\n- ".join(sorted(missing_products))
                + "\n\nกรุณารันก่อน:\n"
                + "python manage.py seed_shop"
            )

        # ========================================================
        # 3. ตรวจสอบ Location
        # ========================================================
        location_names = {
            item["location"]
            for item in self.RESERVATIONS
        }

        locations = {
            location.name: location
            for location in Location.objects.filter(
                name__in=location_names
            )
        }

        missing_locations = [
            name
            for name in location_names
            if name not in locations
        ]

        if missing_locations:
            raise CommandError(
                "ไม่พบ Location ต่อไปนี้:\n- "
                + "\n- ".join(sorted(missing_locations))
                + "\n\nกรุณารันก่อน:\n"
                + "python manage.py seed_shop"
            )

        # ========================================================
        # 4. สร้าง Reservation
        # ========================================================
        now = timezone.now()

        created_count = 0
        updated_count = 0

        for item in self.RESERVATIONS:

            product = products[item["product"]]
            location = locations[item["location"]]

            expires_at = (
                now
                + timedelta(minutes=item["expires_minutes"])
            )

            picked_up_at = None
            cancelled_at = None

            if item["status"] == "picked_up":
                picked_up_at = now - timedelta(
                    days=2
                )

            elif item["status"] == "cancelled":
                cancelled_at = now - timedelta(
                    days=3
                )

            reservation, created = Reservation.objects.get_or_create(
                reservation_code=item["code"],
                defaults={
                    "customer_id": item["customer_id"],
                    "product": product,
                    "location": location,
                    "quantity": item["quantity"],
                    "status": item["status"],
                    "expires_at": expires_at,
                    "picked_up_at": picked_up_at,
                    "cancelled_at": cancelled_at,
                },
            )

            # ----------------------------------------------------
            # ถ้ามีข้อมูลเดิม ให้ update
            # ----------------------------------------------------
            if not created:

                reservation.customer_id = item["customer_id"]
                reservation.product = product
                reservation.location = location
                reservation.quantity = item["quantity"]
                reservation.status = item["status"]
                reservation.expires_at = expires_at
                reservation.picked_up_at = picked_up_at
                reservation.cancelled_at = cancelled_at

                reservation.save()

                updated_count += 1

            else:
                created_count += 1

            # ----------------------------------------------------
            # ปรับ reserved_at ให้ข้อมูล Dashboard ดูสมจริง
            # ----------------------------------------------------
            if item["status"] == "pending":
                reservation.reserved_at = now - timedelta(
                    minutes=30
                )

            elif item["status"] == "picked_up":
                reservation.reserved_at = now - timedelta(
                    days=3
                )

            elif item["status"] == "expired":
                reservation.reserved_at = now - timedelta(
                    days=2
                )

            elif item["status"] == "cancelled":
                reservation.reserved_at = now - timedelta(
                    days=4
                )

            reservation.save(
                update_fields=[
                    "reserved_at",
                ]
            )

        # ========================================================
        # 5. สรุปผล
        # ========================================================
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "สร้างข้อมูล Dashboard สำเร็จ"
            )
        )

        self.stdout.write(
            f"สร้างใหม่ : {created_count} รายการ"
        )

        self.stdout.write(
            f"อัปเดต : {updated_count} รายการ"
        )

        self.stdout.write("")

        # ========================================================
        # 6. แสดงจำนวน Reservation ตาม Status
        # ========================================================
        pending_count = Reservation.objects.filter(
            status="pending"
        ).count()

        picked_up_count = Reservation.objects.filter(
            status="picked_up"
        ).count()

        expired_count = Reservation.objects.filter(
            status="expired"
        ).count()

        cancelled_count = Reservation.objects.filter(
            status="cancelled"
        ).count()

        self.stdout.write("Reservation Summary")
        self.stdout.write(
            f"  Pending   : {pending_count}"
        )
        self.stdout.write(
            f"  Picked Up : {picked_up_count}"
        )
        self.stdout.write(
            f"  Expired   : {expired_count}"
        )
        self.stdout.write(
            f"  Cancelled : {cancelled_count}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "=== เสร็จสิ้น ==="
            )
        )