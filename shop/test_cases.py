"""Integration tests for shop forms, public pages, and admin CRUD flows."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .form import CategoryModelForm, LocationModelForm, ProductModelForm
from .models import Category, Location, Product, ProductLocation


class ShopModelAndFormTests(TestCase):
    """Verify create/update validation and model constraints for shop data."""

    def setUp(self):
        self.category = Category.objects.create(name="อุปกรณ์ไอที")

    def product_data(self, **overrides):
        """Return valid product form data with one field optionally overridden."""
        data = {
            "name": "เมาส์ไร้สาย",
            "description": "สินค้าเพื่อการทดสอบ",
            "price": "299.00",
            "category": self.category.pk,
            "reservable": "True",
        }
        data.update(overrides)
        return data

    def test_product_create_accepts_valid_data(self):
        """TC-CREATE-001: valid product data creates a database record."""
        form = ProductModelForm(data=self.product_data())
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.name, "เมาส์ไร้สาย")
        self.assertEqual(Product.objects.count(), 1)

    def test_product_update_preserves_record_and_changes_price(self):
        """TC-UPDATE-001: editing a product updates fields without duplicating it."""
        product = Product.objects.create(name="เมาส์ไร้สาย", price=299, category=self.category)
        form = ProductModelForm(data=self.product_data(price="349.00"), instance=product)
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(updated.price, 349)

    def test_product_validation_rejects_negative_price(self):
        """TC-VALIDATE-001: negative prices are rejected by the form."""
        form = ProductModelForm(data=self.product_data(price="-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_product_validation_rejects_invalid_category(self):
        """TC-VALIDATE-002: a category ID not in the database is rejected."""
        form = ProductModelForm(data=self.product_data(category=999999))
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_product_name_strips_normal_whitespace(self):
        """TC-VALIDATE-003: normal leading and trailing whitespace is stripped by the form field."""
        form = ProductModelForm(data=self.product_data(name="  เมาส์ไร้สาย  "))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "เมาส์ไร้สาย")

    def test_location_and_category_forms_accept_valid_data(self):
        """TC-CREATE-002: valid location and category forms are accepted."""
        location = LocationModelForm(data={"name": "จุดรับ A", "building": "อาคาร 1"})
        category = CategoryModelForm(data={"name": "เครื่องเขียน", "description": ""})
        self.assertTrue(location.is_valid(), location.errors)
        self.assertTrue(category.is_valid(), category.errors)

    def test_product_location_unique_constraint_prevents_duplicate_pair(self):
        """TC-ERROR-001: one product cannot have duplicate stock rows at one location."""
        location = Location.objects.create(name="จุดรับ A", building="อาคาร 1")
        product = Product.objects.create(name="สายชาร์จ", price=100, category=self.category)
        ProductLocation.objects.create(product=product, location=location, stock=2)
        duplicate = ProductLocation(product=product, location=location, stock=3)
        with self.assertRaises(ValidationError):
            duplicate.validate_constraints()


class ShopPublicAndCrudTests(TestCase):
    """Verify read pages and admin create/update/delete behavior."""

    def setUp(self):
        self.category = Category.objects.create(name="สินค้า")
        self.admin = get_user_model().objects.create_user(
            username="admin", password="Strong-pass-123", role="admin"
        )
        self.client.force_login(self.admin)

    def test_public_product_list_reads_products_and_filters_by_search(self):
        """TC-READ-001: public product listing returns matching search results."""
        Product.objects.create(name="คีย์บอร์ด", price=500, category=self.category)
        Product.objects.create(name="สาย USB", price=50, category=self.category)
        response = self.client.get(reverse("public_products"), {"q": "คีย์บอร์ด"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p.name for p in response.context["products"]], ["คีย์บอร์ด"])

    def test_public_product_list_filters_by_category_and_location(self):
        """TC-FILTER-001: public product listing filters by category and pickup location."""
        other_category = Category.objects.create(name="อุปกรณ์เสริม")
        location = Location.objects.create(name="จุดรับสินค้า", building="อาคาร 1")
        product = Product.objects.create(name="แฟลชไดรฟ์", price=200, category=other_category)
        ProductLocation.objects.create(product=product, location=location, stock=4)
        response = self.client.get(reverse("public_products"), {
            "category": other_category.pk, "location": location.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["products"]), [product])
        self.assertEqual(response.context["selected_location"], str(location.pk))

    def test_admin_product_list_searches_and_filters_by_category(self):
        """TC-FILTER-002: admin product page combines name search with category filter."""
        other_category = Category.objects.create(name="อุปกรณ์เสริม")
        matching = Product.objects.create(name="เมาส์เกมมิ่ง", price=700, category=other_category)
        Product.objects.create(name="เมาส์สำนักงาน", price=300, category=self.category)
        response = self.client.get(reverse("products"), {
            "q": "เกมมิ่ง", "category": other_category.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"]), [matching])

    def test_admin_location_search_filters_by_name(self):
        """TC-FILTER-003: admin location page returns only locations matching the query."""
        Location.objects.create(name="อาคารวิศวกรรม", building="อาคาร 1")
        Location.objects.create(name="โรงอาหารกลาง", building="อาคาร 2")
        response = self.client.get(reverse("locations"), {"q": "วิศวกรรม"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item.name for item in response.context["page_obj"]], ["อาคารวิศวกรรม"])

    def test_admin_category_search_filters_by_name(self):
        """TC-FILTER-004: admin category page returns only categories matching the query."""
        Category.objects.create(name="เครื่องดื่ม")
        Category.objects.create(name="เครื่องแต่งกาย")
        response = self.client.get(reverse("categories"), {"q": "เครื่องดื่ม"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item.name for item in response.context["page_obj"]], ["เครื่องดื่ม"])

    def test_admin_can_create_update_and_delete_category(self):
        """TC-CRUD-001: admin completes category create, update, and delete flows."""
        response = self.client.post(reverse("categories"), {"save": "", "name": "ใหม่"})
        self.assertRedirects(response, reverse("categories"))
        category = Category.objects.get(name="ใหม่")
        self.client.post(reverse("categories"), {"save": category.pk, "name": "แก้ไข"})
        category.refresh_from_db()
        self.assertEqual(category.name, "แก้ไข")
        self.client.post(reverse("categories"), {"delete": category.pk})
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_admin_can_create_update_and_delete_location(self):
        """TC-CRUD-002: admin completes location create, update, and delete flows."""
        response = self.client.post(
            reverse("locations"), {"save": "", "name": "จุดรับ", "building": "อาคาร 2"}
        )
        self.assertRedirects(response, reverse("locations"))
        location = Location.objects.get(name="จุดรับ")
        self.client.post(
            reverse("locations"), {"save": location.pk, "name": "จุดรับใหม่", "building": "อาคาร 2"}
        )
        location.refresh_from_db()
        self.assertEqual(location.name, "จุดรับใหม่")
        self.client.post(reverse("locations"), {"delete": location.pk})
        self.assertFalse(Location.objects.filter(pk=location.pk).exists())

    def test_admin_can_create_update_and_delete_product(self):
        """TC-CRUD-003: admin completes product create, update, and delete flows."""
        data = {"save": "", "name": "สินค้าใหม่", "price": "10", "category": self.category.pk, "reservable": "True"}
        response = self.client.post(reverse("products"), data)
        self.assertRedirects(response, reverse("products"))
        product = Product.objects.get(name="สินค้าใหม่")
        data.update({"save": product.pk, "name": "สินค้าแก้ไข", "price": "20"})
        self.client.post(reverse("products"), data)
        product.refresh_from_db()
        self.assertEqual(product.name, "สินค้าแก้ไข")
        self.client.post(reverse("products"), {"delete": product.pk})
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
