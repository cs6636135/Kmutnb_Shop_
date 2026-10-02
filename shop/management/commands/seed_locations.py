from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Location


LOCATIONS = (
    {
        "name": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
        "building": "อาคารสำนักหอสมุด",
        "floor": "ชั้น 1",
        "room": "ร้านสวัสดิการ",
        "description": (
            "จุดจำหน่ายสินค้าสวัสดิการสำหรับนักศึกษาและบุคลากร "
            "ตั้งอยู่บริเวณชั้น 1 ของอาคารสำนักหอสมุด "
            "สามารถเลือกซื้อเครื่องแต่งกาย อุปกรณ์การเรียน "
            "ของที่ระลึก และสินค้าอื่น ๆ ที่เกี่ยวข้องกับมหาวิทยาลัย"
        ),
        "image_url": "",
    },
    {
        "name": "ร้านสวัสดิการ โรงอาหารกลาง",
        "building": "โรงอาหารกลาง",
        "floor": "ชั้น 1",
        "room": "บริเวณหน้าทางเข้า",
        "description": (
            "จุดจำหน่ายสินค้าสวัสดิการบริเวณโรงอาหารกลาง "
            "เหมาะสำหรับนักศึกษาและบุคลากรที่ต้องการเลือกซื้อสินค้า "
            "ระหว่างการใช้บริการโรงอาหารหรือเดินทางผ่านบริเวณดังกล่าว"
        ),
        "image_url": "",
    },
    {
        "name": "ร้านสวัสดิการ อาคาร 46",
        "building": "อาคาร 46",
        "floor": "ชั้น 1",
        "room": "ร้านค้าสวัสดิการ",
        "description": (
            "ร้านค้าสวัสดิการสำหรับนักศึกษาและบุคลากร "
            "ให้บริการจำหน่ายสินค้าและอุปกรณ์ที่เกี่ยวข้องกับการใช้ชีวิต "
            "และการเรียนภายในมหาวิทยาลัย รวมถึงสินค้าเครื่องแต่งกาย "
            "ของที่ระลึก และอุปกรณ์สำหรับนักศึกษา"
        ),
        "image_url": "",
    },
    {
        "name": "จุดรับสินค้า อาคารกิจกรรมนักศึกษา",
        "building": "อาคารกิจกรรมนักศึกษา",
        "floor": "ชั้น 1",
        "room": "จุดรับสินค้า",
        "description": (
            "จุดรับสินค้าสำหรับนักศึกษาและบุคลากรที่ทำรายการสั่งซื้อหรือจองสินค้า "
            "สามารถใช้เป็นจุดสำหรับรับสินค้าตามรายการที่กำหนด "
            "เหมาะสำหรับการให้บริการรับสินค้าภายในมหาวิทยาลัย"
        ),
        "image_url": "",
    },
    {
        "name": "จุดบริการนักศึกษา อาคารอเนกประสงค์",
        "building": "อาคารอเนกประสงค์",
        "floor": "ชั้น 1",
        "room": "เคาน์เตอร์บริการ",
        "description": (
            "จุดบริการสำหรับนักศึกษาและบุคลากรภายในอาคารอเนกประสงค์ "
            "ใช้สำหรับให้บริการและอำนวยความสะดวกเกี่ยวกับสินค้า "
            "การรับสินค้า และข้อมูลที่เกี่ยวข้องกับร้านค้าสวัสดิการ"
        ),
        "image_url": "",
    },
    {
        "name": "ร้านค้าสวัสดิการ อาคารเรียนรวม",
        "building": "อาคารเรียนรวม",
        "floor": "ชั้น 1",
        "room": "ร้านค้าสวัสดิการ",
        "description": (
            "จุดจำหน่ายสินค้าสวัสดิการใกล้พื้นที่การเรียนการสอน "
            "เหมาะสำหรับนักศึกษาและบุคลากรที่ต้องการซื้ออุปกรณ์ "
            "เครื่องแต่งกาย หนังสือ และสินค้าอื่น ๆ "
            "ระหว่างการเข้าเรียนหรือทำกิจกรรมภายในมหาวิทยาลัย"
        ),
        "image_url": "",
    },
    {
        "name": "จุดรับสินค้า อาคารวิศวกรรม",
        "building": "อาคารวิศวกรรม",
        "floor": "ชั้น 1",
        "room": "จุดรับสินค้า",
        "description": (
            "จุดรับสินค้าสำหรับนักศึกษาและบุคลากรในพื้นที่อาคารวิศวกรรม "
            "เหมาะสำหรับการรับหนังสือ อุปกรณ์การเรียน "
            "เครื่องแต่งกาย และสินค้าที่ทำรายการจองหรือสั่งซื้อไว้ล่วงหน้า"
        ),
        "image_url": "",
    },
    {
        "name": "ร้านสวัสดิการ อาคารเทคโนโลยีสารสนเทศ",
        "building": "อาคารเทคโนโลยีสารสนเทศ",
        "floor": "ชั้น 1",
        "room": "ร้านค้าสวัสดิการ",
        "description": (
            "จุดจำหน่ายสินค้าสวัสดิการสำหรับนักศึกษาและบุคลากร "
            "ในพื้นที่อาคารเทคโนโลยีสารสนเทศ "
            "เหมาะสำหรับเลือกซื้อหนังสือ อุปกรณ์การเรียน "
            "ของใช้ และสินค้าอื่น ๆ ที่เกี่ยวข้อง"
        ),
        "image_url": "",
    },
)


class Command(BaseCommand):
    help = "Seed shop locations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview locations without saving them.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.show_dry_run()
            return

        created = 0
        skipped = 0

        with transaction.atomic():
            for location_data in LOCATIONS:
                location, was_created = Location.objects.get_or_create(
                    name=location_data["name"],
                    building=location_data["building"],
                    defaults={
                        "floor": location_data["floor"],
                        "room": location_data["room"],
                        "description": location_data["description"],
                        "image_url": location_data["image_url"],
                    },
                )

                if was_created:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Created location: {location.name}")
                    )
                else:
                    skipped += 1
                    self.stdout.write(f"Skipped existing location: {location.name}")

        self.stdout.write(self.style.SUCCESS(
            f"Location seed complete: {created} created, {skipped} skipped."
        ))

    def show_dry_run(self):
        for location_data in LOCATIONS:
            exists = Location.objects.filter(
                name=location_data["name"],
                building=location_data["building"],
            ).exists()
            action = "exists" if exists else "would create"
            self.stdout.write(f'Location [{action}]: {location_data["name"]}')
