from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Category, Product


CATEGORY_NAMES = (
    "อุปกรณ์จัดชุด",
    "เครื่องแต่งกาย",
    "ของที่ระลึก",
    "เครื่องหมาย",
    "เบ็ดเตล็ด",
)

PRODUCTS = (
    {
        "name": "เข็มนักศึกษา",
        "category": "อุปกรณ์จัดชุด",
        "description": "เข็มนักศึกษาสำหรับเครื่องแบบนักศึกษา",
        "price": "45.00",
    },
    {
        "name": "เสื้อคอกลม",
        "category": "เครื่องแต่งกาย",
        "description": "เสื้อคอกลมสำหรับนักศึกษาและบุคลากร",
        "price": "180.00",
    },
    {
        "name": "เสื้อโปโล",
        "category": "เครื่องแต่งกาย",
        "description": "เสื้อโปโลสำหรับสวมใส่ในมหาวิทยาลัย",
        "price": "350.00",
    },
    {
        "name": "กางเกง",
        "category": "เครื่องแต่งกาย",
        "description": "กางเกงเครื่องแบบสำหรับนักศึกษา",
        "price": "450.00",
    },
    {
        "name": "กระเป๋าช็อปปิ้ง",
        "category": "ของที่ระลึก",
        "description": "กระเป๋าช็อปปิ้งสำหรับใช้ในชีวิตประจำวัน",
        "price": "120.00",
    },
    {
        "name": "กระเป๋าเป้",
        "category": "ของที่ระลึก",
        "description": "กระเป๋าเป้สำหรับพกพาหนังสือและอุปกรณ์",
        "price": "590.00",
    },
    {
        "name": "เข็มมหาวิทยาลัย",
        "category": "เครื่องหมาย",
        "description": "เข็มตรามหาวิทยาลัยสำหรับติดเครื่องแบบ",
        "price": "80.00",
    },
    {
        "name": "กระดุม",
        "category": "เครื่องหมาย",
        "description": "กระดุมสำหรับเครื่องแบบนักศึกษา",
        "price": "15.00",
    },
    {
        "name": "เครื่องหมายมหาวิทยาลัย",
        "category": "เครื่องหมาย",
        "description": "เครื่องหมายมหาวิทยาลัยสำหรับติดเครื่องแบบ",
        "price": "60.00",
    },
    {
        "name": "ของใช้ทั่วไป",
        "category": "เบ็ดเตล็ด",
        "description": "ของใช้จำเป็นสำหรับนักศึกษาและบุคลากร",
        "price": "99.00",
    },
)


class Command(BaseCommand):
    help = "Seed the initial welfare shop categories and products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which records would be created without saving them.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.show_dry_run()
            return

        created_categories = 0
        created_products = 0

        with transaction.atomic():
            categories = {}
            for name in CATEGORY_NAMES:
                category = Category.objects.filter(name=name).order_by("pk").first()
                if category is None:
                    category = Category.objects.create(name=name, description="")
                    created_categories += 1
                categories[name] = category

            for product_data in PRODUCTS:
                existing = Product.objects.filter(
                    name=product_data["name"]
                ).order_by("pk").first()
                if existing is not None:
                    self.stdout.write(
                        f'Skipped existing product: {product_data["name"]}'
                    )
                    continue

                Product.objects.create(
                    name=product_data["name"],
                    description=product_data["description"],
                    price=product_data["price"],
                    image_url="",
                    reservable=True,
                    category=categories[product_data["category"]],
                )
                created_products += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created_categories} categories and "
            f"{created_products} products created."
        ))

    def show_dry_run(self):
        for name in CATEGORY_NAMES:
            exists = Category.objects.filter(name=name).exists()
            action = "exists" if exists else "would create"
            self.stdout.write(f"Category [{action}]: {name}")

        for product_data in PRODUCTS:
            exists = Product.objects.filter(name=product_data["name"]).exists()
            action = "exists" if exists else "would create"
            self.stdout.write(
                f'Product [{action}]: {product_data["name"]} '
                f'-> {product_data["category"]} ({product_data["price"]} THB)'
            )
