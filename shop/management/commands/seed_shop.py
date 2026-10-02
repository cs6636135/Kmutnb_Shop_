from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Category, Product, ProductLocation, Location


# =========================================================
# CATEGORY
# =========================================================

CATEGORY_NAMES = (
    "อุปกรณ์จัดชุด",
    "เครื่องแต่งกาย",
    "ของที่ระลึก",
    "เครื่องหมาย",
    "หนังสือ",
)


# =========================================================
# BOOKS
# =========================================================

BOOKS = (
    {
        "name": "คณิตศาสตร์วิศวกรรม 1",
        "course_code": "010213001",
        "price": "180.00",
    },
    {
        "name": "คณิตศาสตร์วิศวกรรม 2",
        "course_code": "010213002",
        "price": "190.00",
    },
    {
        "name": "ฟิสิกส์วิศวกรรม 1",
        "course_code": "010213101",
        "price": "180.00",
    },
    {
        "name": "ฟิสิกส์วิศวกรรม 2",
        "course_code": "010213102",
        "price": "190.00",
    },
    {
        "name": "เคมีสำหรับวิศวกร",
        "course_code": "010213201",
        "price": "175.00",
    },
    {
        "name": "กลศาสตร์วิศวกรรม",
        "course_code": "010113201",
        "price": "200.00",
    },
    {
        "name": "กลศาสตร์วัสดุ",
        "course_code": "010113301",
        "price": "220.00",
    },
    {
        "name": "วัสดุวิศวกรรม",
        "course_code": "010113302",
        "price": "210.00",
    },
    {
        "name": "กระบวนการผลิต",
        "course_code": "010113401",
        "price": "220.00",
    },
    {
        "name": "เทอร์โมไดนามิกส์",
        "course_code": "010113501",
        "price": "230.00",
    },
    {
        "name": "กลศาสตร์ของไหล",
        "course_code": "010113601",
        "price": "220.00",
    },
    {
        "name": "การถ่ายเทความร้อน",
        "course_code": "010113701",
        "price": "230.00",
    },
    {
        "name": "วงจรไฟฟ้าและอิเล็กทรอนิกส์เบื้องต้น",
        "course_code": "010213301",
        "price": "200.00",
    },
    {
        "name": "ระบบดิจิทัล",
        "course_code": "010213401",
        "price": "190.00",
    },
    {
        "name": "การเขียนโปรแกรมคอมพิวเตอร์",
        "course_code": "020113101",
        "price": "180.00",
    },
    {
        "name": "โครงสร้างข้อมูลและอัลกอริทึม",
        "course_code": "020113201",
        "price": "220.00",
    },
    {
        "name": "ฐานข้อมูลเบื้องต้น",
        "course_code": "020113301",
        "price": "200.00",
    },
    {
        "name": "ระบบปฏิบัติการ",
        "course_code": "020113401",
        "price": "220.00",
    },
    {
        "name": "การสื่อสารข้อมูลและเครือข่าย",
        "course_code": "020113501",
        "price": "230.00",
    },
    {
        "name": "สถิติสำหรับวิศวกร",
        "course_code": "010213501",
        "price": "180.00",
    },
)


BOOK_PRODUCTS = tuple(
    {
        "name": book["name"],
        "category": "หนังสือ",
        "description": (
            f"หนังสือประกอบการเรียนสำหรับนักศึกษา "
            f"มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ "
            f"ในรายวิชา {book['name']} "
            f"รหัสวิชา {book['course_code']} "
            "จัดทำขึ้นเพื่อสนับสนุนการเรียนการสอนและการศึกษาด้วยตนเอง "
            "โดยเนื้อหาครอบคลุมแนวคิดพื้นฐาน หลักการสำคัญ "
            "ตัวอย่างประกอบ และเนื้อหาที่เกี่ยวข้องกับรายวิชา "
            "เหมาะสำหรับใช้ประกอบการเรียนในชั้นเรียน "
            "การอ่านทบทวนบทเรียน การทำแบบฝึกหัด "
            "การเตรียมตัวสอบกลางภาคและปลายภาค "
            "รวมถึงใช้เป็นเอกสารอ้างอิงสำหรับการศึกษาเพิ่มเติม"
        ),
        "price": book["price"],
        "image_url": "",
        "reservable": True,
    }
    for book in BOOKS
)


# =========================================================
# OTHER PRODUCTS
# =========================================================

BASE_PRODUCTS = (
    {
        "name": "เข็มนักศึกษา",
        "category": "อุปกรณ์จัดชุด",
        "description": (
            "เข็มนักศึกษาสำหรับใช้ประกอบเครื่องแบบนักศึกษา "
            "เหมาะสำหรับการจัดเตรียมเครื่องแบบให้ครบถ้วนและเรียบร้อย "
            "ใช้สำหรับการเรียน การสอบ และกิจกรรมภายในมหาวิทยาลัย "
            "เหมาะสำหรับนักศึกษาที่ต้องการจัดชุดเครื่องแบบสำหรับการใช้งานประจำวัน"
        ),
        "price": "45.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "เสื้อคอกลม",
        "category": "เครื่องแต่งกาย",
        "description": (
            "เสื้อคอกลมสำหรับนักศึกษาและบุคลากร "
            "เหมาะสำหรับสวมใส่ในชีวิตประจำวัน กิจกรรมทั่วไป "
            "และกิจกรรมภายในมหาวิทยาลัย "
            "รูปแบบเรียบง่าย สามารถสวมใส่ได้หลากหลายโอกาส"
        ),
        "price": "180.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "เสื้อโปโล",
        "category": "เครื่องแต่งกาย",
        "description": (
            "เสื้อโปโลสำหรับนักศึกษาและบุคลากร "
            "เหมาะสำหรับการสวมใส่ในมหาวิทยาลัย "
            "กิจกรรมของคณะหรือหน่วยงาน "
            "รวมถึงกิจกรรมที่ต้องการความสุภาพมากกว่าเสื้อยืดทั่วไป"
        ),
        "price": "350.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "กางเกง",
        "category": "เครื่องแต่งกาย",
        "description": (
            "กางเกงสำหรับใช้ร่วมกับเครื่องแบบนักศึกษา "
            "เหมาะสำหรับการเรียน การสอบ และกิจกรรมภายในมหาวิทยาลัย "
            "ออกแบบให้สามารถใช้งานร่วมกับเครื่องแต่งกายของนักศึกษาได้อย่างเหมาะสม"
        ),
        "price": "450.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "กระเป๋าช็อปปิ้ง",
        "category": "ของที่ระลึก",
        "description": (
            "กระเป๋าสำหรับใช้งานในชีวิตประจำวัน "
            "เหมาะสำหรับใส่หนังสือ เอกสาร อุปกรณ์การเรียน "
            "และสิ่งของทั่วไป สามารถใช้สำหรับเดินทางไปเรียน "
            "ซื้อสินค้า หรือทำกิจกรรมภายในมหาวิทยาลัย"
        ),
        "price": "120.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "กระเป๋าเป้",
        "category": "ของที่ระลึก",
        "description": (
            "กระเป๋าเป้สำหรับนักศึกษาและบุคลากร "
            "เหมาะสำหรับพกพาหนังสือ เอกสาร อุปกรณ์การเรียน "
            "โน้ตบุ๊ก และของใช้ส่วนตัว "
            "สามารถใช้สำหรับเดินทางไปเรียนหรือทำกิจกรรมภายในมหาวิทยาลัย"
        ),
        "price": "590.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "เข็มมหาวิทยาลัย",
        "category": "เครื่องหมาย",
        "description": (
            "เข็มตรามหาวิทยาลัยสำหรับติดบนเครื่องแบบ "
            "หรือเครื่องแต่งกายที่เหมาะสม "
            "ใช้สำหรับแสดงสัญลักษณ์ของมหาวิทยาลัย "
            "เหมาะสำหรับนักศึกษาและบุคลากร"
        ),
        "price": "80.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "กระดุม",
        "category": "เครื่องหมาย",
        "description": (
            "กระดุมสำหรับใช้กับเครื่องแบบนักศึกษา "
            "เหมาะสำหรับเปลี่ยนทดแทนกระดุมเดิมที่ชำรุดหรือสูญหาย "
            "สามารถจัดเก็บไว้เป็นอะไหล่สำหรับเครื่องแบบ "
            "เพื่อให้เครื่องแต่งกายพร้อมใช้งานอยู่เสมอ"
        ),
        "price": "15.00",
        "image_url": "",
        "reservable": True,
    },
    {
        "name": "เครื่องหมายมหาวิทยาลัย",
        "category": "เครื่องหมาย",
        "description": (
            "เครื่องหมายมหาวิทยาลัยสำหรับใช้ประกอบเครื่องแบบนักศึกษา "
            "ช่วยให้การแต่งกายมีความเรียบร้อย "
            "และแสดงถึงสัญลักษณ์ของมหาวิทยาลัย "
            "เหมาะสำหรับการเรียน การสอบ และกิจกรรมที่เกี่ยวข้องกับมหาวิทยาลัย"
        ),
        "price": "60.00",
        "image_url": "",
        "reservable": True,
    },
)


PRODUCTS = BASE_PRODUCTS + BOOK_PRODUCTS


# =========================================================
# LOCATIONS
# =========================================================

LOCATIONS = (
    {
        "name": "ร้านสวัสดิการ อาคารสำนักหอสมุด",
        "building": "อาคารสำนักหอสมุด",
        "floor": "ชั้น 1",
        "room": "ร้านสวัสดิการ",
        "description": (
            "จุดจำหน่ายสินค้าและหนังสือสวัสดิการ "
            "สำหรับนักศึกษาและบุคลากรภายในมหาวิทยาลัย "
            "เหมาะสำหรับการซื้อหนังสือประกอบการเรียน "
            "เครื่องแต่งกาย อุปกรณ์จัดชุด และของที่ระลึก"
        ),
        "image_url": "",
    },
    {
        "name": "ร้านสวัสดิการ โรงอาหารกลาง",
        "building": "โรงอาหารกลาง",
        "floor": "ชั้น 1",
        "room": "หน้าทางเข้า",
        "description": (
            "จุดจำหน่ายสินค้าสวัสดิการบริเวณโรงอาหารกลาง "
            "เหมาะสำหรับนักศึกษาและบุคลากรที่ต้องการเลือกซื้อ "
            "เครื่องแต่งกาย อุปกรณ์จัดชุด เครื่องหมาย "
            "และของที่ระลึก"
        ),
        "image_url": "",
    },
)


# =========================================================
# STOCK
# =========================================================

BOOKS_OUT_OF_STOCK = (
    "คณิตศาสตร์วิศวกรรม 2",
    "เคมีสำหรับวิศวกร",
    "ระบบปฏิบัติการ",
)


BOOK_STOCK_LEVELS = {
    book["name"]: (
        (0, 0)
        if book["name"] in BOOKS_OUT_OF_STOCK
        else (12, 8)
    )
    for book in BOOKS
}


STOCK_LEVELS = {
    "เข็มนักศึกษา": (24, 12),
    "เสื้อคอกลม": (18, 8),
    "เสื้อโปโล": (14, 6),
    "กางเกง": (10, 5),
    "กระเป๋าช็อปปิ้ง": (20, 10),
    "กระเป๋าเป้": (8, 4),
    "เข็มมหาวิทยาลัย": (30, 15),
    "กระดุม": (50, 25),
    "เครื่องหมายมหาวิทยาลัย": (24, 12),
    **BOOK_STOCK_LEVELS,
}


# =========================================================
# HELPERS
# =========================================================

def changed_fields(instance, desired_values):
    return {
        field: value
        for field, value in desired_values.items()
        if getattr(instance, field) != value
    }


def save_changed_fields(instance, desired_values):
    updates = changed_fields(instance, desired_values)

    if updates:
        for field, value in updates.items():
            setattr(instance, field, value)

        instance.save(update_fields=list(updates))

    return updates


# =========================================================
# COMMAND
# =========================================================

class Command(BaseCommand):

    help = "Seed KMUTNB Shop categories, products, locations and stock."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="แสดงข้อมูลที่จะสร้างโดยไม่บันทึกลงฐานข้อมูล",
        )

    def handle(self, *args, **options):

        if options["dry_run"]:
            self.show_dry_run()
            return

        created_categories = 0
        updated_categories = 0

        created_products = 0
        updated_products = 0

        created_locations = 0
        updated_locations = 0

        created_product_locations = 0
        updated_product_locations = 0

        with transaction.atomic():

            # =====================================================
            # CATEGORIES
            # =====================================================

            categories = {}

            for name in CATEGORY_NAMES:

                description = (
                    f"หมวดหมู่สินค้า {name} "
                    "สำหรับนักศึกษาและบุคลากร "
                    "ภายใต้ร้านสวัสดิการมหาวิทยาลัย"
                )

                category = (
                    Category.objects
                    .filter(name=name)
                    .order_by("pk")
                    .first()
                )

                if category is None:

                    category = Category.objects.create(
                        name=name,
                        description=description,
                    )

                    created_categories += 1

                elif save_changed_fields(
                    category,
                    {
                        "description": description,
                    },
                ):

                    updated_categories += 1

                categories[name] = category

            # =====================================================
            # PRODUCTS
            # =====================================================

            for product_data in PRODUCTS:

                existing = (
                    Product.objects
                    .filter(name=product_data["name"])
                    .order_by("pk")
                    .first()
                )

                desired_values = {
                    "description": product_data["description"],
                    "price": Decimal(product_data["price"]),
                    "image_url": product_data["image_url"],
                    "reservable": product_data["reservable"],
                    "category": categories[
                        product_data["category"]
                    ],
                }

                if existing is not None:

                    updates = save_changed_fields(
                        existing,
                        desired_values,
                    )

                    if updates:
                        updated_products += 1

                        self.stdout.write(
                            f'Updated product: {product_data["name"]}'
                        )

                    continue

                Product.objects.create(
                    name=product_data["name"],
                    description=product_data["description"],
                    price=product_data["price"],
                    image_url=product_data["image_url"],
                    reservable=product_data["reservable"],
                    category=categories[
                        product_data["category"]
                    ],
                )

                created_products += 1

            # =====================================================
            # LOCATIONS
            # =====================================================

            locations = {}

            for location_data in LOCATIONS:

                location = (
                    Location.objects
                    .filter(
                        name=location_data["name"],
                        building=location_data["building"],
                    )
                    .order_by("pk")
                    .first()
                )

                if location is None:

                    location = Location.objects.create(
                        **location_data
                    )

                    created_locations += 1

                else:

                    updates = save_changed_fields(
                        location,
                        {
                            key: value
                            for key, value in location_data.items()
                            if key not in {
                                "name",
                                "building",
                            }
                        },
                    )

                    if updates:
                        updated_locations += 1

                locations[location_data["name"]] = location

            # =====================================================
            # PRODUCT LOCATION / STOCK
            # =====================================================

            for product_name, stock_counts in STOCK_LEVELS.items():

                product = (
                    Product.objects
                    .filter(name=product_name)
                    .order_by("pk")
                    .first()
                )

                if product is None:
                    continue

                for location_data, stock in zip(
                    LOCATIONS,
                    stock_counts,
                ):

                    location = locations[
                        location_data["name"]
                    ]

                    product_location, created = (
                        ProductLocation.objects.get_or_create(
                            product=product,
                            location=location,
                            defaults={
                                "stock": stock,
                            },
                        )
                    )

                    if created:

                        created_product_locations += 1

                    elif product_location.stock != stock:

                        product_location.stock = stock

                        product_location.save(
                            update_fields=["stock"]
                        )

                        updated_product_locations += 1

        # =========================================================
        # SUMMARY
        # =========================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "========================================"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "       KMUTNB SHOP SEED COMPLETE"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "========================================"
            )
        )

        self.stdout.write(
            f"Categories  : {created_categories} created / "
            f"{updated_categories} updated"
        )

        self.stdout.write(
            f"Products    : {created_products} created / "
            f"{updated_products} updated"
        )

        self.stdout.write(
            f"Locations   : {created_locations} created / "
            f"{updated_locations} updated"
        )

        self.stdout.write(
            f"Stock       : {created_product_locations} created / "
            f"{updated_product_locations} updated"
        )

        self.stdout.write("")

    # =============================================================
    # DRY RUN
    # =============================================================

    def show_dry_run(self):

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "========== DRY RUN =========="
            )
        )

        self.stdout.write("")
        self.stdout.write("Categories:")

        for name in CATEGORY_NAMES:
            self.stdout.write(f"  - {name}")

        self.stdout.write("")
        self.stdout.write(
            f"Products: {len(PRODUCTS)} รายการ"
        )

        self.stdout.write(
            f"Books: {len(BOOK_PRODUCTS)} รายการ"
        )

        self.stdout.write(
            f"Locations: {len(LOCATIONS)} รายการ"
        )

        self.stdout.write("")
