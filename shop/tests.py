
from io import BytesIO
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .form import ProductModelForm
from .models import Category, Location, Product, ProductLocation
from reservations.models import Reservation


class ProductFormTest(TestCase):
    def setUp(self):
        # สร้างหมวดหมู่ไว้ใช้ในทุกเทส (ถ้า Category ของคุณมี field อื่นที่บังคับ ให้เติมตรงนี้)
        self.category = Category.objects.create(name="มือถือ")

    def make_data(self, **overrides):
        """ข้อมูลที่ถูกต้องทั้งหมด แล้วแก้เฉพาะช่องที่อยากเทส"""
        data = {
            "name": "iPhone 17",
            "description": "",
            "price": "100.00",
            "reservable": "True",
            "category": self.category.pk,
        }
        data.update(overrides)
        return data

    def assertFieldInvalid(self, data, field):
        """Assert the form is invalid and reports an error for the expected field."""
        form = ProductModelForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(field, form.errors)

    def assertFieldErrorCode(self, data, field, code):
        form = ProductModelForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()[field][0].code, code)

    # ---------- ข้อมูลถูกต้อง ----------

    def test_valid_data(self):
        form = ProductModelForm(data=self.make_data())
        self.assertTrue(form.is_valid(), form.errors)

    # ---------- ชื่อสินค้า ----------

    def test_name_empty(self):
        self.assertFieldInvalid(self.make_data(name=""), "name")

    def test_name_only_spaces(self):
        self.assertFieldInvalid(self.make_data(name="     "), "name")

    def test_name_only_invisible_chars(self):
        # มีแต่อักขระล่องหน ต้องถือว่าว่าง
        self.assertFieldInvalid(self.make_data(name="\u200b\ufeff"), "name")

    def test_name_only_each_invisible_char(self):
        for invisible_char in ("\u200b", "\ufeff"):
            with self.subTest(invisible_char=repr(invisible_char)):
                self.assertFieldInvalid(self.make_data(name=invisible_char), "name")

    def test_name_too_long(self):
        self.assertFieldInvalid(self.make_data(name="a" * 151), "name")

    def test_name_exactly_150_ok(self):
        form = ProductModelForm(data=self.make_data(name="a" * 150))
        self.assertTrue(form.is_valid(), form.errors)

    def test_name_invisible_chars_removed(self):
        form = ProductModelForm(data=self.make_data(name="\ufeffIphone\u200b17 "))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Iphone17")

    def test_name_duplicate(self):
        Product.objects.create(name="euphoria", price=10, category=self.category)
        self.assertFieldErrorCode(self.make_data(name="euphoria"), "name", "unique")

    def test_name_duplicate_with_invisible_chars(self):
        # ชื่อเดิมมีอยู่แล้ว แต่คนกรอกแอบมีอักขระล่องหน ต้องถือว่าซ้ำ
        Product.objects.create(name="euphoria", price=10, category=self.category)
        self.assertFieldErrorCode(self.make_data(name="euphoria\u200b"), "name", "unique")

    def test_name_duplicate_with_bom(self):
        Product.objects.create(name="euphoria", price=10, category=self.category)
        self.assertFieldErrorCode(self.make_data(name="\ufeffeuphoria"), "name", "unique")

    def test_name_different_case_is_allowed(self):
        # ตัวเล็ก/ใหญ่ถือเป็นคนละชื่อ
        Product.objects.create(name="iphone", price=10, category=self.category)
        form = ProductModelForm(data=self.make_data(name="iPhone"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_edit_product_keep_same_name(self):
        # แก้ไขสินค้าเดิมโดยไม่เปลี่ยนชื่อ ต้องไม่ error ว่าซ้ำกับตัวเอง
        product = Product.objects.create(name="euphoria", price=10, category=self.category)
        form = ProductModelForm(
            data=self.make_data(name="euphoria", price="20"), instance=product
        )
        self.assertTrue(form.is_valid(), form.errors)

    # ---------- ราคา ----------

    def test_price_empty(self):
        self.assertFieldInvalid(self.make_data(price=""), "price")

    def test_price_not_a_number(self):
        self.assertFieldInvalid(self.make_data(price="abc"), "price")

    def test_price_negative(self):
        self.assertFieldInvalid(self.make_data(price="-1"), "price")

    def test_price_zero_allowed(self):
        form = ProductModelForm(data=self.make_data(price="0"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_price_two_decimals_ok(self):
        form = ProductModelForm(data=self.make_data(price="10.99"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_price_too_many_decimals(self):
        self.assertFieldInvalid(self.make_data(price="10.011"), "price")

    def test_price_too_many_whole_digits(self):
        # ตัวเลขหน้าจุดได้ไม่เกิน 8 หลัก (10 - 2)
        self.assertFieldInvalid(self.make_data(price="123456789.00"), "price")

    # ---------- อัปโหลดรูปภาพ ----------

    def make_image_upload(self):
        image_file = BytesIO()
        Image.new("RGB", (1, 1), color="red").save(image_file, format="PNG")
        return SimpleUploadedFile(
            "product.png",
            image_file.getvalue(),
            content_type="image/png",
        )

    def test_image_is_optional(self):
        form = ProductModelForm(data=self.make_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_image_upload_is_rejected(self):
        invalid_image = SimpleUploadedFile(
            "not-an-image.txt",
            b"not an image",
            content_type="text/plain",
        )
        form = ProductModelForm(
            data=self.make_data(),
            files={"image": invalid_image},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    @patch("shop.form.upload_image")
    def test_image_upload_saves_supabase_url(self, upload_image):
        image = self.make_image_upload()
        expected_url = (
            "https://example.supabase.co/storage/v1/object/public/"
            "img/products/test.jpg"
        )
        upload_image.return_value = expected_url
        form = ProductModelForm(data=self.make_data(), files={"image": image})

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        saved_product = Product.objects.get(pk=product.pk)

        self.assertEqual(saved_product.image_url, expected_url)
        upload_image.assert_called_once_with(image, folder="products")

    def test_edit_without_new_image_keeps_existing_image_url(self):
        product = Product.objects.create(
            name="Existing product",
            price=10,
            category=self.category,
            image_url="https://example.com/existing.jpg",
        )
        form = ProductModelForm(
            data=self.make_data(name=product.name),
            instance=product,
        )

        self.assertTrue(form.is_valid(), form.errors)
        updated_product = form.save()

        self.assertEqual(updated_product.image_url, "https://example.com/existing.jpg")

    @patch("shop.form.upload_image")
    def test_upload_rejects_invalid_supabase_url(self, upload_image):
        image = self.make_image_upload()
        upload_image.return_value = "not-a-url"
        form = ProductModelForm(data=self.make_data(), files={"image": image})

        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaises(ValidationError):
            form.save()
        self.assertFalse(Product.objects.exists())

    @patch("shop.form.upload_image")
    def test_upload_rejects_supabase_url_over_255_characters(self, upload_image):
        image = self.make_image_upload()
        base_url = "https://example.supabase.co/"
        overlong_url = base_url + "a" * (256 - len(base_url))
        upload_image.return_value = overlong_url
        form = ProductModelForm(data=self.make_data(), files={"image": image})

        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaises(ValidationError):
            form.save()
        self.assertFalse(Product.objects.exists())

    # ---------- หมวดหมู่ ----------

    def test_category_missing(self):
        self.assertFieldInvalid(self.make_data(category=""), "category")

    def test_category_not_exist(self):
        self.assertFieldInvalid(self.make_data(category=99999), "category")

    # ---------- จองได้หรือไม่ ----------

    def test_reservable_invalid_choice(self):
        self.assertFieldInvalid(self.make_data(reservable="abc"), "reservable")

    def test_reservable_false_ok(self):
        form = ProductModelForm(data=self.make_data(reservable="False"))
        self.assertTrue(form.is_valid(), form.errors)


class ProductImageUrlFieldTest(TestCase):
    def setUp(self):
        self.image_url_field = Product._meta.get_field("image_url")

    def test_image_url_field_allows_blank(self):
        self.assertEqual(self.image_url_field.clean("", None), "")

    def test_image_url_field_accepts_valid_url(self):
        url = "https://example.com/product.jpg"
        self.assertEqual(self.image_url_field.clean(url, None), url)

    def test_image_url_field_rejects_invalid_url(self):
        with self.assertRaises(ValidationError):
            self.image_url_field.clean("not-a-url", None)

    def test_image_url_field_accepts_255_characters(self):
        prefix = "https://example.com/"
        url = prefix + "a" * (255 - len(prefix))

        self.assertEqual(len(url), 255)
        self.assertEqual(self.image_url_field.clean(url, None), url)

    def test_image_url_field_rejects_more_than_255_characters(self):
        prefix = "https://example.com/"
        url = prefix + "a" * (256 - len(prefix))

        self.assertEqual(len(url), 256)
        with self.assertRaises(ValidationError):
            self.image_url_field.clean(url, None)


class ProductSearchTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test category")
        admin = get_user_model().objects.create_user(
            username="product-admin",
            password="test-password",
            role="admin",
        )
        self.client.force_login(admin)
        Product.objects.create(name="iPhone 17", price=100, category=self.category)
        Product.objects.create(name="Wireless Mouse", price=20, category=self.category)

    def search(self, q, **extra):
        response = self.client.get(reverse("products"), {"q": q}, **extra)
        self.assertEqual(response.status_code, 200)
        return [product.name for product in response.context["page_obj"]]

    def test_search_is_case_insensitive(self):
        self.assertEqual(self.search("IPHONE"), ["iPhone 17"])

    def test_search_matches_multiple_terms_in_any_order(self):
        self.assertEqual(self.search("17 iphone"), ["iPhone 17"])

    def test_search_ignores_extra_spaces(self):
        self.assertEqual(self.search("  wireless   mouse "), ["Wireless Mouse"])

    def test_empty_search_returns_all_products(self):
        self.assertEqual(len(self.search("")), 2)

    def test_search_works_with_htmx_request(self):
        self.assertEqual(
            self.search("mouse", HTTP_HX_REQUEST="true"),
            ["Wireless Mouse"],
        )

    def test_category_filter_returns_only_products_in_selected_category(self):
        other_category = Category.objects.create(name="Accessories")
        Product.objects.create(name="USB Cable", price=8, category=other_category)

        response = self.client.get(reverse("products"), {"category": other_category.pk})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.name for product in response.context["page_obj"]],
            ["USB Cable"],
        )
        self.assertContains(response, 'id="product-category-filter"')
        self.assertContains(response, f'value="{other_category.pk}" selected')

    def test_category_filter_combines_with_name_search(self):
        other_category = Category.objects.create(name="Accessories")
        Product.objects.create(name="Wireless Keyboard", price=30, category=other_category)

        response = self.client.get(
            reverse("products"),
            {"q": "wireless", "category": other_category.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.name for product in response.context["page_obj"]],
            ["Wireless Keyboard"],
        )
        self.assertEqual(response.context["search_query"], "wireless")
        self.assertEqual(response.context["category_query"], str(other_category.pk))

    def test_pagination_keeps_search_results(self):
        for i in range(12):
            Product.objects.create(name=f"Cable {i}", price=5, category=self.category)

        response = self.client.get(reverse("products"), {"q": "cable", "page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 2)  # 12 อัน หน้าละ 10 → หน้า 2 มี 2

    def test_pagination_keeps_category_filter(self):
        for i in range(12):
            Product.objects.create(name=f"Category product {i}", price=5, category=self.category)

        response = self.client.get(
            reverse("products"),
            {"category": self.category.pk, "page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 4)
        self.assertContains(response, f"category={self.category.pk}&amp;page=1")


class LocationManagementTest(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user(
            username="location-admin",
            password="test-password",
            role="admin",
        )
        self.client.force_login(admin)

    def test_location_list_page_renders(self):
        Location.objects.create(name="Main building", building="Building 1")

        response = self.client.get(reverse("locations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main building")
        self.assertContains(response, "จัดการจุดจำหน่าย")

    def test_location_form_renders_and_saves(self):
        form_response = self.client.get(reverse("location_create"))

        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "เพิ่มจุดจำหน่าย")

        response = self.client.post(
            reverse("location_create"),
            {
                "name": "Pickup point",
                "building": "Building 2",
                "floor": "1",
                "room": "101",
                "description": "North entrance",
            },
        )

        self.assertRedirects(response, reverse("locations"))
        self.assertTrue(
            Location.objects.filter(
                name="Pickup point",
                building="Building 2",
                floor="1",
                room="101",
                description="North entrance",
            ).exists()
        )


class CategoryManagementTest(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user(
            username="category-admin",
            password="test-password",
            role="admin",
        )
        self.client.force_login(admin)

    def test_category_list_page_renders_categories(self):
        parent = Category.objects.create(name="Stationery")
        Category.objects.create(name="Notebooks", parent=parent, description="Paper goods")

        response = self.client.get(reverse("categories"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "จัดการหมวดหมู่สินค้า")
        self.assertContains(response, "Notebooks")
        self.assertContains(response, "Stationery")
        self.assertContains(response, "Paper goods")

    def test_category_form_renders_and_saves(self):
        form_response = self.client.get(reverse("category_create"))

        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "เพิ่มหมวดหมู่สินค้า")
        self.assertNotContains(form_response, 'name="parent"')

        response = self.client.post(
            reverse("category_create"),
            {
                "name": "Notebooks",
                "description": "Paper goods",
            },
        )

        self.assertRedirects(response, reverse("categories"))
        self.assertTrue(
            Category.objects.filter(
                name="Notebooks",
                description="Paper goods",
                parent__isnull=True,
            ).exists()
        )

    def test_edit_form_does_not_expose_parent_field(self):
        category = Category.objects.create(name="Stationery")

        response = self.client.get(reverse("category_edit", args=[category.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("parent", response.context["form"].fields)
        self.assertNotContains(response, 'name="parent"')

    def test_category_used_by_product_cannot_be_deleted(self):
        category = Category.objects.create(name="Stationery")
        Product.objects.create(name="Notebook", price=10, category=category)

        response = self.client.post(
            reverse("category_delete", args=[category.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("categories"))
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())
        self.assertContains(response, "ไม่สามารถลบหมวดหมู่ได้ เนื่องจากยังมีข้อมูลที่เกี่ยวข้องอยู่")


class DashboardTest(TestCase):
    def test_admin_dashboard_renders(self):
        admin = get_user_model().objects.create_user(
            username="dashboard-admin",
            password="test-password",
            role="admin",
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_admin"])
        self.assertContains(response, "สต็อกรวมทุกสาขา")

    def test_staff_dashboard_renders_for_assigned_location(self):
        location = Location.objects.create(name="Main building", building="Building 1")
        staff = get_user_model().objects.create_user(
            username="dashboard-staff",
            password="test-password",
            role="staff",
            location=location,
        )
        self.client.force_login(staff)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_admin"])
        self.assertContains(response, "Main building")
        self.assertEqual(response.context["locations_summary"], [])

    def test_admin_location_summary_matches_stock_and_pending_reservations(self):
        admin = get_user_model().objects.create_user(
            username="dashboard-summary-admin",
            password="test-password",
            role="admin",
        )
        category = Category.objects.create(name="Dashboard summary category")
        product_one = Product.objects.create(
            name="Dashboard summary product one",
            price="10.00",
            category=category,
        )
        product_two = Product.objects.create(
            name="Dashboard summary product two",
            price="20.00",
            category=category,
        )
        location_one = Location.objects.create(
            name="Summary location one",
            building="Building 1",
        )
        location_two = Location.objects.create(
            name="Summary location two",
            building="Building 2",
        )
        empty_location = Location.objects.create(
            name="Empty location",
            building="Building 3",
        )
        ProductLocation.objects.create(
            product=product_one,
            location=location_one,
            stock=4,
        )
        ProductLocation.objects.create(
            product=product_two,
            location=location_one,
            stock=6,
        )
        ProductLocation.objects.create(
            product=product_one,
            location=location_two,
            stock=3,
        )

        expires_at = timezone.now() + timedelta(hours=1)
        for code, location, status in (
            ("SUMMARY-PENDING-1", location_one, Reservation.Status.PENDING),
            ("SUMMARY-PENDING-2", location_one, Reservation.Status.PENDING),
            ("SUMMARY-CANCELLED", location_one, Reservation.Status.CANCELLED),
            ("SUMMARY-PENDING-3", location_two, Reservation.Status.PENDING),
        ):
            Reservation.objects.create(
                reservation_code=code,
                customer_id="1234567890123",
                product=product_one,
                location=location,
                quantity=1,
                status=status,
                expires_at=expires_at,
            )

        self.client.force_login(admin)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        summary_by_location = {
            row["location"]["name"]: row
            for row in response.context["locations_summary"]
        }
        self.assertEqual(
            summary_by_location,
            {
                "Summary location one": {
                    "location": {"name": "Summary location one"},
                    "total_stock": 10,
                    "active_reservations": 2,
                },
                "Summary location two": {
                    "location": {"name": "Summary location two"},
                    "total_stock": 3,
                    "active_reservations": 1,
                },
                "Empty location": {
                    "location": {"name": "Empty location"},
                    "total_stock": 0,
                    "active_reservations": 0,
                },
            },
        )


@override_settings(DEBUG=False)
class NotFoundBehaviorTest(TestCase):
    def test_unknown_url_displays_custom_404_page(self):
        response = self.client.get("/manage/unknown-page/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "ไม่พบหน้าที่ต้องการ", status_code=404)

    def test_missing_product_displays_custom_404_page(self):
        response = self.client.get(
            reverse("product_detail", kwargs={"product_id": 999999})
        )

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "ไม่พบหน้าที่ต้องการ", status_code=404)

    def test_product_search_without_results_stays_on_search_page(self):
        response = self.client.get(
            reverse("public_products"),
            {"q": "สินค้าที่ไม่มีอยู่จริง"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ไม่พบสินค้าที่ตรงกับเงื่อนไข")

    def test_unknown_reservation_code_stays_on_status_page(self):
        response = self.client.post(
            reverse("reservation_status"),
            {"reservation_code": "UNKNOWN-RESERVATION"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ไม่พบรายการจองจากรหัสที่ระบุ")
